from __future__ import annotations

import uuid
from typing import Any

from app.db.surreal import SurrealStore
from app.models import Pipeline
from app.repositories._common import coerce_datetime, normalise_id, now


class PipelineRepository:
    table = "pipeline"

    def __init__(self, store: SurrealStore) -> None:
        self._store = store

    async def list(self) -> list[Pipeline]:
        rows = await self._store.select_all(self.table, order_by="created_at DESC")
        return [self._to_model(r) for r in rows]

    async def get(self, pipeline_id: str) -> Pipeline | None:
        row = await self._store.select_one(self.table, pipeline_id)
        return self._to_model(row) if row else None

    async def get_by_name(self, name: str) -> Pipeline | None:
        rows = await self._store.select_all(
            self.table, where="name = $name", params={"name": name}, limit=1
        )
        return self._to_model(rows[0]) if rows else None

    async def list_enabled_with_schedule(self) -> list[Pipeline]:
        rows = await self._store.select_all(self.table, where="enabled = true")
        # SurrealDB nullable comparisons are version-sensitive, so we
        # filter for a non-empty schedule string in Python — there are
        # never enough pipelines for this to matter.
        return [self._to_model(r) for r in rows if (r.get("schedule") or "")]

    async def list_yaml_sourced(self) -> list[Pipeline]:
        rows = await self._store.select_all(
            self.table,
            where="definition_source = 'yaml'",
        )
        return [self._to_model(r) for r in rows]

    async def create(self, *, data: dict[str, Any]) -> Pipeline:
        ts = now()
        record_id = data.pop("id", None) or str(uuid.uuid4())
        payload = self._defaults() | data
        payload["created_at"] = ts.isoformat()
        payload["updated_at"] = ts.isoformat()
        row = await self._store.create(self.table, record_id, payload)
        return self._to_model(row)

    async def upsert_by_name(self, *, name: str, data: dict[str, Any]) -> Pipeline:
        """Used by the YAML loader: update if a pipeline with this name
        exists, otherwise create. Preserves the existing record id so
        downstream references (jobs, assets) stay stable."""
        existing = await self.get_by_name(name)
        merged = self._defaults() | {"name": name} | data
        if existing is None:
            merged["created_at"] = now().isoformat()
            merged["updated_at"] = now().isoformat()
            row = await self._store.create(self.table, str(uuid.uuid4()), merged)
        else:
            merged["updated_at"] = now().isoformat()
            row = await self._store.update(self.table, existing.id, merged)
            if row is None:
                raise RuntimeError(f"update returned no row for pipeline {existing.id}")
        return self._to_model(row)

    async def update(self, pipeline_id: str, patch: dict[str, Any]) -> Pipeline | None:
        if not patch:
            return await self.get(pipeline_id)
        data = dict(patch)
        data["updated_at"] = now().isoformat()
        row = await self._store.update(self.table, pipeline_id, data)
        return self._to_model(row) if row else None

    async def delete(self, pipeline_id: str) -> bool:
        return await self._store.delete(self.table, pipeline_id)

    async def count(self) -> int:
        return await self._store.count(self.table)

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _defaults() -> dict[str, Any]:
        return {
            "description": None,
            "mode": "full",
            "field_mappings": [],
            "transform": {},
            "schedule": None,
            "enabled": True,
            "incremental_field": None,
            "key_columns": [],
            "definition_source": "ui",
            "definition_path": None,
        }

    @staticmethod
    def _to_model(row: dict[str, Any]) -> Pipeline:
        return Pipeline(
            id=normalise_id(row.get("id")),
            name=row["name"],
            description=row.get("description"),
            source_connection_id=row["source_connection_id"],
            destination_connection_id=row["destination_connection_id"],
            source_object=row["source_object"],
            destination_object=row["destination_object"],
            mode=row.get("mode") or "full",
            field_mappings=list(row.get("field_mappings") or []),
            transform=dict(row.get("transform") or {}),
            schedule=row.get("schedule"),
            enabled=bool(row.get("enabled", True)),
            incremental_field=row.get("incremental_field"),
            key_columns=list(row.get("key_columns") or []),
            definition_source=row.get("definition_source") or "ui",
            definition_path=row.get("definition_path"),
            created_at=coerce_datetime(row.get("created_at")) or now(),
            updated_at=coerce_datetime(row.get("updated_at")) or now(),
        )
