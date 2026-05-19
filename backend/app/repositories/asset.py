from __future__ import annotations

import uuid
from typing import Any

from app.db.surreal import SurrealStore
from app.models import Asset, AssetMaterialization
from app.repositories._common import coerce_datetime, normalise_id, now


class AssetRepository:
    table = "asset"

    def __init__(self, store: SurrealStore) -> None:
        self._store = store

    async def list(self) -> list[Asset]:
        rows = await self._store.select_all(self.table, order_by="key")
        return [self._to_model(r) for r in rows]

    async def list_for_pipeline(self, pipeline_id: str) -> list[Asset]:
        rows = await self._store.select_all(
            self.table,
            where="pipeline_id = $pid",
            params={"pid": pipeline_id},
        )
        return [self._to_model(r) for r in rows]

    async def list_with_freshness_policy(self) -> list[Asset]:
        # SurrealDB's empty-object comparison is version-sensitive, so
        # we fetch and filter in Python — the dataset is small (one
        # row per declared asset) and the loop is trivial.
        rows = await self._store.select_all(self.table)
        return [self._to_model(r) for r in rows if (r.get("freshness_policy") or {})]

    async def get_by_key(self, key: str) -> Asset | None:
        rows = await self._store.select_all(
            self.table, where="key = $key", params={"key": key}, limit=1
        )
        return self._to_model(rows[0]) if rows else None

    async def upsert(
        self,
        *,
        key: str,
        pipeline_id: str,
        description: str | None = None,
        connection_id: str | None = None,
        object_name: str | None = None,
        depends_on: list[str] | None = None,
        asset_metadata: dict[str, Any] | None = None,
        freshness_policy: dict[str, Any] | None = None,
        definition_path: str | None = None,
    ) -> Asset:
        existing = await self.get_by_key(key)
        payload = {
            "key": key,
            "pipeline_id": pipeline_id,
            "description": description,
            "connection_id": connection_id,
            "object_name": object_name,
            "depends_on": list(depends_on or []),
            "asset_metadata": dict(asset_metadata or {}),
            "freshness_policy": dict(freshness_policy or {}),
            "definition_path": definition_path,
            "updated_at": now().isoformat(),
        }
        if existing is None:
            payload["created_at"] = now().isoformat()
            row = await self._store.create(self.table, str(uuid.uuid4()), payload)
        else:
            row = await self._store.update(self.table, existing.id, payload)
            if row is None:
                raise RuntimeError(f"update returned no row for asset {existing.id}")
        return self._to_model(row)

    async def delete(self, asset_id: str) -> bool:
        return await self._store.delete(self.table, asset_id)

    @staticmethod
    def _to_model(row: dict[str, Any]) -> Asset:
        return Asset(
            id=normalise_id(row.get("id")),
            key=row["key"],
            description=row.get("description"),
            pipeline_id=row["pipeline_id"],
            connection_id=row.get("connection_id"),
            object_name=row.get("object_name"),
            depends_on=list(row.get("depends_on") or []),
            asset_metadata=dict(row.get("asset_metadata") or {}),
            freshness_policy=dict(row.get("freshness_policy") or {}),
            definition_path=row.get("definition_path"),
            created_at=coerce_datetime(row.get("created_at")) or now(),
            updated_at=coerce_datetime(row.get("updated_at")) or now(),
        )


class AssetMaterializationRepository:
    table = "asset_materialization"

    def __init__(self, store: SurrealStore) -> None:
        self._store = store

    async def record(
        self,
        *,
        asset_key: str,
        job_id: str,
        pipeline_id: str,
        rows_written: int,
        dag_run_id: str | None = None,
    ) -> AssetMaterialization:
        ts = now()
        record_id = str(uuid.uuid4())
        data = {
            "asset_key": asset_key,
            "job_id": job_id,
            "pipeline_id": pipeline_id,
            "dag_run_id": dag_run_id,
            "rows_written": rows_written,
            "ts": ts.isoformat(),
        }
        row = await self._store.create(self.table, record_id, data)
        return self._to_model(row)

    async def latest_per_asset(self) -> dict[str, AssetMaterialization]:
        """Returns the most recent materialization for every asset key."""
        rows = await self._store.select_all(self.table, order_by="ts DESC")
        out: dict[str, AssetMaterialization] = {}
        for r in rows:
            m = self._to_model(r)
            out.setdefault(m.asset_key, m)
        return out

    async def list_for_asset(
        self, asset_key: str, *, limit: int = 50
    ) -> list[AssetMaterialization]:
        rows = await self._store.select_all(
            self.table,
            where="asset_key = $k",
            params={"k": asset_key},
            order_by="ts DESC",
            limit=limit,
        )
        return [self._to_model(r) for r in rows]

    async def list_for_dag_run(self, dag_run_id: str) -> list[AssetMaterialization]:
        rows = await self._store.select_all(
            self.table,
            where="dag_run_id = $r",
            params={"r": dag_run_id},
        )
        return [self._to_model(r) for r in rows]

    @staticmethod
    def _to_model(row: dict[str, Any]) -> AssetMaterialization:
        return AssetMaterialization(
            id=normalise_id(row.get("id")),
            asset_key=row["asset_key"],
            job_id=row["job_id"],
            pipeline_id=row["pipeline_id"],
            dag_run_id=row.get("dag_run_id"),
            rows_written=int(row.get("rows_written") or 0),
            ts=coerce_datetime(row.get("ts")) or now(),
        )
