from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.db.surreal import SurrealStore
from app.models import DagRun, JobStatus
from app.repositories._common import coerce_datetime, normalise_id, now


class DagRunRepository:
    table = "dag_run"

    def __init__(self, store: SurrealStore) -> None:
        self._store = store

    async def list(self, *, limit: int = 50) -> list[DagRun]:
        rows = await self._store.select_all(
            self.table, order_by="started_at DESC", limit=limit
        )
        return [self._to_model(r) for r in rows]

    async def get(self, run_id: str) -> DagRun | None:
        row = await self._store.select_one(self.table, run_id)
        return self._to_model(row) if row else None

    async def list_running(self) -> list[DagRun]:
        rows = await self._store.select_all(
            self.table,
            where="status = $s",
            params={"s": JobStatus.RUNNING.value},
        )
        return [self._to_model(r) for r in rows]

    async def create(
        self,
        *,
        triggered_by: str,
        requested_assets: list[str],
        resolved_assets: list[str],
    ) -> DagRun:
        ts = now()
        record_id = str(uuid.uuid4())
        data = {
            "triggered_by": triggered_by,
            "requested_assets": list(requested_assets),
            "resolved_assets": list(resolved_assets),
            "status": JobStatus.RUNNING.value,
            "started_at": ts.isoformat(),
            "finished_at": None,
        }
        row = await self._store.create(self.table, record_id, data)
        return self._to_model(row)

    async def update(self, run_id: str, patch: dict[str, Any]) -> DagRun | None:
        data: dict[str, Any] = {}
        for k, v in patch.items():
            data[k] = v.isoformat() if isinstance(v, datetime) else v
        row = await self._store.update(self.table, run_id, data)
        return self._to_model(row) if row else None

    @staticmethod
    def _to_model(row: dict[str, Any]) -> DagRun:
        return DagRun(
            id=normalise_id(row.get("id")),
            triggered_by=row.get("triggered_by") or "manual",
            requested_assets=list(row.get("requested_assets") or []),
            resolved_assets=list(row.get("resolved_assets") or []),
            status=row.get("status") or JobStatus.RUNNING.value,
            started_at=coerce_datetime(row.get("started_at")) or now(),
            finished_at=coerce_datetime(row.get("finished_at")),
        )
