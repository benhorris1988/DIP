"""YAML pipeline definition loader.

Files under ``settings.definitions_dir`` are the source of truth for
pipelines marked ``definition_source='yaml'``. The loader:

1. Reads every ``*.yaml`` / ``*.yml`` file in the directory.
2. Validates the structure with pydantic.
3. Resolves connection names → IDs against the current DB.
4. Validates the asset DAG (no cycles, all upstream keys exist).
5. Upserts pipelines and assets, transactionally.
6. Tombstones YAML pipelines whose file has been removed.

The loader returns a :class:`LoadReport` so the API can surface the
result in the UI. The DB is the materialised view; the YAML files are
truth.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Asset, Connection, Pipeline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# YAML schema
# ---------------------------------------------------------------------------


class SourceSpec(BaseModel):
    connection: str  # connection NAME
    object: str
    incremental_field: str | None = None


class DestinationSpec(BaseModel):
    connection: str
    object: str


class FieldMappingSpec(BaseModel):
    source: str
    destination: str
    transform: str | None = None


class PipelineSpec(BaseModel):
    name: str
    description: str | None = None
    mode: str = Field(default="full")
    schedule: str | None = None
    enabled: bool = True
    source: SourceSpec
    destination: DestinationSpec
    field_mappings: list[FieldMappingSpec] = Field(default_factory=list)

    @field_validator("mode")
    @classmethod
    def _valid_mode(cls, v: str) -> str:
        if v not in {"full", "incremental", "upsert"}:
            raise ValueError(f"invalid mode: {v}")
        return v


class FreshnessSpec(BaseModel):
    """How stale an asset is allowed to get before the auto-materializer
    schedules a fresh run. Either field may be set; whichever produces
    the shorter window wins."""

    max_age_minutes: int | None = Field(default=None, ge=1)
    max_age_hours: float | None = Field(default=None, gt=0)

    def to_max_age_seconds(self) -> int | None:
        candidates: list[int] = []
        if self.max_age_minutes is not None:
            candidates.append(self.max_age_minutes * 60)
        if self.max_age_hours is not None:
            candidates.append(int(self.max_age_hours * 3600))
        return min(candidates) if candidates else None


class AssetSpec(BaseModel):
    key: str
    description: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    freshness: FreshnessSpec | None = None


class DefinitionFile(BaseModel):
    pipeline: PipelineSpec
    assets: list[AssetSpec] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Load report
# ---------------------------------------------------------------------------


@dataclass
class LoadEntry:
    path: str
    pipeline: str | None = None
    assets: list[str] = field(default_factory=list)
    action: str = "synced"  # synced | error | removed
    error: str | None = None


@dataclass
class LoadReport:
    directory: str
    entries: list[LoadEntry] = field(default_factory=list)
    removed_pipelines: list[str] = field(default_factory=list)
    pipelines_total: int = 0
    assets_total: int = 0
    errors: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "directory": self.directory,
            "pipelines_total": self.pipelines_total,
            "assets_total": self.assets_total,
            "errors": self.errors,
            "removed_pipelines": self.removed_pipelines,
            "entries": [
                {
                    "path": e.path,
                    "pipeline": e.pipeline,
                    "assets": e.assets,
                    "action": e.action,
                    "error": e.error,
                }
                for e in self.entries
            ],
        }


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class DefinitionError(Exception):
    pass


def _read_files(root: Path) -> list[tuple[Path, DefinitionFile]]:
    parsed: list[tuple[Path, DefinitionFile]] = []
    errors: list[tuple[Path, str]] = []
    for p in sorted(root.rglob("*.y*ml")):
        if p.suffix.lower() not in {".yaml", ".yml"}:
            continue
        try:
            with p.open() as fh:
                raw = yaml.safe_load(fh)
            if raw is None:
                continue
            parsed.append((p, DefinitionFile.model_validate(raw)))
        except (yaml.YAMLError, ValidationError) as exc:
            errors.append((p, str(exc)))
    if errors:
        # Stash errors on the function via attribute trick — they're returned
        # alongside the parsed files in load_definitions, see below.
        _read_files.errors = errors  # type: ignore[attr-defined]
    else:
        _read_files.errors = []  # type: ignore[attr-defined]
    return parsed


def _detect_cycles(asset_keys: dict[str, list[str]]) -> list[str]:
    """Returns the keys in any cycle, or [] if the DAG is acyclic.

    Uses Kahn's algorithm: drain nodes with in-degree 0 from the graph
    and any survivors are part of (or downstream of) a cycle.
    """
    in_degree = {k: 0 for k in asset_keys}
    for k, deps in asset_keys.items():
        for d in deps:
            if d in in_degree:
                in_degree[k] += 1
    queue = [k for k, deg in in_degree.items() if deg == 0]
    visited: set[str] = set()
    while queue:
        n = queue.pop()
        visited.add(n)
        for k, deps in asset_keys.items():
            if n in deps:
                in_degree[k] -= 1
                if in_degree[k] == 0 and k not in visited:
                    queue.append(k)
    return [k for k in asset_keys if k not in visited]


async def load_definitions(db: AsyncSession) -> LoadReport:
    settings = get_settings()
    root = Path(settings.definitions_dir).resolve()
    report = LoadReport(directory=str(root))

    if not root.exists():
        return report

    parsed = _read_files(root)
    parse_errors: list[tuple[Path, str]] = getattr(_read_files, "errors", [])
    for path, err in parse_errors:
        report.entries.append(
            LoadEntry(path=str(path), action="error", error=err)
        )
        report.errors += 1

    # Index connections by name for resolution
    conns = (await db.execute(select(Connection))).scalars().all()
    conn_by_name = {c.name: c for c in conns}

    # Collect declared assets across all files for DAG validation
    declared_asset_keys: dict[str, list[str]] = {}
    for _, defn in parsed:
        for asset in defn.assets:
            declared_asset_keys[asset.key] = list(asset.depends_on)

    cycle_nodes = _detect_cycles(declared_asset_keys)
    if cycle_nodes:
        # Refuse the whole load on cycles — partial loads would leave the DB
        # in a confusing state.
        report.entries.append(
            LoadEntry(
                path=str(root),
                action="error",
                error=f"asset graph has cycles involving: {', '.join(sorted(cycle_nodes))}",
            )
        )
        report.errors += 1
        return report

    # Validate that every referenced upstream key is declared somewhere
    for key, deps in declared_asset_keys.items():
        for d in deps:
            if d not in declared_asset_keys:
                # Allow assets defined manually in the DB to be referenced too
                existing = (
                    await db.execute(select(Asset).where(Asset.key == d))
                ).scalar_one_or_none()
                if not existing:
                    report.entries.append(
                        LoadEntry(
                            path="(graph)",
                            action="error",
                            error=f"asset {key!r} depends_on unknown key {d!r}",
                        )
                    )
                    report.errors += 1

    if report.errors:
        return report

    # Snapshot existing YAML-sourced pipelines so we can tombstone removed ones
    existing_yaml = (
        (await db.execute(select(Pipeline).where(Pipeline.definition_source == "yaml")))
        .scalars()
        .all()
    )
    existing_by_name = {p.name: p for p in existing_yaml}
    seen_names: set[str] = set()

    for path, defn in parsed:
        entry = LoadEntry(path=str(path), pipeline=defn.pipeline.name)
        try:
            src_conn = conn_by_name.get(defn.pipeline.source.connection)
            dst_conn = conn_by_name.get(defn.pipeline.destination.connection)
            if not src_conn:
                raise DefinitionError(
                    f"source connection {defn.pipeline.source.connection!r} not found"
                )
            if not dst_conn:
                raise DefinitionError(
                    f"destination connection {defn.pipeline.destination.connection!r} not found"
                )
            existing = existing_by_name.get(defn.pipeline.name)
            if existing is None:
                # Also check for a UI-created pipeline with the same name —
                # YAML wins, but we refuse the load to avoid silently
                # clobbering UI work.
                conflict = (
                    await db.execute(
                        select(Pipeline).where(Pipeline.name == defn.pipeline.name)
                    )
                ).scalar_one_or_none()
                if conflict and conflict.definition_source != "yaml":
                    raise DefinitionError(
                        f"name conflict: a UI pipeline named "
                        f"{defn.pipeline.name!r} already exists"
                    )
                existing = Pipeline(id=str(uuid.uuid4()), name=defn.pipeline.name)
                db.add(existing)

            existing.description = defn.pipeline.description
            existing.source_connection_id = src_conn.id
            existing.destination_connection_id = dst_conn.id
            existing.source_object = defn.pipeline.source.object
            existing.destination_object = defn.pipeline.destination.object
            existing.mode = defn.pipeline.mode
            existing.schedule = defn.pipeline.schedule
            existing.enabled = defn.pipeline.enabled
            existing.incremental_field = defn.pipeline.source.incremental_field
            existing.field_mappings = [m.model_dump(exclude_none=True) for m in defn.pipeline.field_mappings]
            existing.definition_source = "yaml"
            existing.definition_path = str(path)
            seen_names.add(defn.pipeline.name)

            # Flush so the pipeline.id is available for asset FK
            await db.flush()

            # Sync assets: upsert by key, tombstone old assets that no longer
            # appear on this pipeline.
            existing_assets = (
                (await db.execute(select(Asset).where(Asset.pipeline_id == existing.id)))
                .scalars()
                .all()
            )
            existing_by_key = {a.key: a for a in existing_assets}
            current_keys: set[str] = set()
            for spec in defn.assets:
                current_keys.add(spec.key)
                a = existing_by_key.get(spec.key)
                if a is None:
                    a = Asset(id=str(uuid.uuid4()), key=spec.key)
                    db.add(a)
                a.description = spec.description
                a.pipeline_id = existing.id
                a.connection_id = dst_conn.id
                a.object_name = defn.pipeline.destination.object
                a.depends_on = list(spec.depends_on)
                a.asset_metadata = dict(spec.metadata)
                a.freshness_policy = (
                    spec.freshness.model_dump(exclude_none=True)
                    if spec.freshness
                    else {}
                )
                a.definition_path = str(path)
                entry.assets.append(spec.key)
                report.assets_total += 1
            for old_key, old_asset in existing_by_key.items():
                if old_key not in current_keys:
                    await db.delete(old_asset)

            report.pipelines_total += 1
        except (DefinitionError, ValueError) as exc:
            entry.action = "error"
            entry.error = str(exc)
            report.errors += 1
        report.entries.append(entry)

    # Tombstone YAML-pipelines whose file has gone away
    for name, pipeline in existing_by_name.items():
        if name not in seen_names:
            await db.delete(pipeline)
            report.removed_pipelines.append(name)

    if report.errors == 0:
        await db.commit()
    else:
        await db.rollback()

    return report
