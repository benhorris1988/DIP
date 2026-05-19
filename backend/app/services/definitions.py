"""YAML pipeline definition loader.

Files under ``settings.definitions_dir`` are the source of truth for
pipelines marked ``definition_source='yaml'``. The loader:

1. Reads every ``*.yaml`` / ``*.yml`` file in the directory.
2. Validates the structure with pydantic.
3. Resolves connection names → IDs against the current metadata store.
4. Validates the asset DAG (no cycles, all upstream keys exist).
5. Upserts pipelines and assets via the repositories.
6. Tombstones YAML pipelines whose file has been removed.

The loader returns a :class:`LoadReport` so the API can surface the
result in the UI.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config import get_settings
from app.db.surreal import SurrealStore
from app.repositories import (
    AssetRepository,
    ConnectionRepository,
    PipelineRepository,
)

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
    key_columns: list[str] = Field(default_factory=list)
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


def _read_files(root: Path) -> tuple[
    list[tuple[Path, DefinitionFile]], list[tuple[Path, str]]
]:
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
    return parsed, errors


def _detect_cycles(asset_keys: dict[str, list[str]]) -> list[str]:
    """Returns the keys in any cycle, or [] if the DAG is acyclic.

    Kahn's algorithm: drain nodes with in-degree 0 and any survivors are
    part of (or downstream of) a cycle.
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


def _freshness_to_dict(spec: FreshnessSpec | None) -> dict[str, Any]:
    if spec is None:
        return {}
    out: dict[str, Any] = {}
    if spec.max_age_minutes is not None:
        out["max_age_minutes"] = spec.max_age_minutes
    if spec.max_age_hours is not None:
        out["max_age_hours"] = spec.max_age_hours
    return out


async def load_definitions(store: SurrealStore) -> LoadReport:
    settings = get_settings()
    root = Path(settings.definitions_dir).resolve()
    report = LoadReport(directory=str(root))

    if not root.exists():
        return report

    connections_repo = ConnectionRepository(store)
    pipelines_repo = PipelineRepository(store)
    assets_repo = AssetRepository(store)

    parsed, parse_errors = _read_files(root)
    for path, err in parse_errors:
        report.entries.append(LoadEntry(path=str(path), action="error", error=err))
        report.errors += 1

    all_connections = await connections_repo.list()
    conn_by_name = {c.name: c for c in all_connections}

    declared_asset_keys: dict[str, list[str]] = {}
    for _, defn in parsed:
        for asset in defn.assets:
            declared_asset_keys[asset.key] = list(asset.depends_on)

    cycle_nodes = _detect_cycles(declared_asset_keys)
    if cycle_nodes:
        report.entries.append(
            LoadEntry(
                path=str(root),
                action="error",
                error=f"asset graph has cycles involving: {', '.join(sorted(cycle_nodes))}",
            )
        )
        report.errors += 1
        return report

    for key, deps in declared_asset_keys.items():
        for d in deps:
            if d in declared_asset_keys:
                continue
            existing = await assets_repo.get_by_key(d)
            if existing is None:
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
    existing_yaml = await pipelines_repo.list_yaml_sourced()
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
            # YAML wins over UI for the same name, but only against another
            # YAML pipeline — refuse to clobber a UI-created pipeline silently.
            conflict = await pipelines_repo.get_by_name(defn.pipeline.name)
            if conflict and conflict.definition_source != "yaml":
                raise DefinitionError(
                    f"name conflict: a UI pipeline named "
                    f"{defn.pipeline.name!r} already exists"
                )

            pipeline = await pipelines_repo.upsert_by_name(
                name=defn.pipeline.name,
                data={
                    "description": defn.pipeline.description,
                    "source_connection_id": src_conn.id,
                    "destination_connection_id": dst_conn.id,
                    "source_object": defn.pipeline.source.object,
                    "destination_object": defn.pipeline.destination.object,
                    "mode": defn.pipeline.mode,
                    "schedule": defn.pipeline.schedule,
                    "enabled": defn.pipeline.enabled,
                    "key_columns": list(defn.pipeline.key_columns),
                    "incremental_field": defn.pipeline.source.incremental_field,
                    "field_mappings": [
                        m.model_dump(exclude_none=True)
                        for m in defn.pipeline.field_mappings
                    ],
                    "definition_source": "yaml",
                    "definition_path": str(path),
                },
            )
            seen_names.add(defn.pipeline.name)

            # Sync assets: upsert by key, then prune those no longer declared.
            existing_assets = await assets_repo.list_for_pipeline(pipeline.id)
            existing_by_key = {a.key: a for a in existing_assets}
            current_keys: set[str] = set()
            for spec in defn.assets:
                current_keys.add(spec.key)
                await assets_repo.upsert(
                    key=spec.key,
                    pipeline_id=pipeline.id,
                    description=spec.description,
                    connection_id=dst_conn.id,
                    object_name=defn.pipeline.destination.object,
                    depends_on=list(spec.depends_on),
                    asset_metadata=dict(spec.metadata),
                    freshness_policy=_freshness_to_dict(spec.freshness),
                    definition_path=str(path),
                )
                entry.assets.append(spec.key)
                report.assets_total += 1
            for old_key, old_asset in existing_by_key.items():
                if old_key not in current_keys:
                    await assets_repo.delete(old_asset.id)

            report.pipelines_total += 1
        except (DefinitionError, ValueError) as exc:
            entry.action = "error"
            entry.error = str(exc)
            report.errors += 1
        report.entries.append(entry)

    # Tombstone YAML-pipelines whose file has gone away
    for name, pipeline in existing_by_name.items():
        if name not in seen_names:
            await pipelines_repo.delete(pipeline.id)
            report.removed_pipelines.append(name)

    return report
