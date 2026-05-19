from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.db.surreal import SurrealStore
from app.models import Job, JobStatus
from app.repositories._common import coerce_datetime, normalise_id, now


class JobRepository:
    table = "job"

    def __init__(self, store: SurrealStore) -> None:
        self._store = store

    async def list(
        self,
        *,
        pipeline_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[Job]:
        where_parts: list[str] = []
        params: dict[str, Any] = {}
        if pipeline_id:
            where_parts.append("pipeline_id = $pid")
            params["pid"] = pipeline_id
        if status:
            where_parts.append("status = $status")
            params["status"] = status
        rows = await self._store.select_all(
            self.table,
            where=" AND ".join(where_parts) if where_parts else None,
            params=params,
            order_by="created_at DESC",
            limit=limit,
        )
        return [self._to_model(r) for r in rows]

    async def list_for_dag_run(self, dag_run_id: str) -> list[Job]:
        rows = await self._store.select_all(
            self.table,
            where="dag_run_id = $rid",
            params={"rid": dag_run_id},
            order_by="created_at",
        )
        return [self._to_model(r) for r in rows]

    async def get(self, job_id: str) -> Job | None:
        row = await self._store.select_one(self.table, job_id)
        return self._to_model(row) if row else None

    async def create(
        self,
        *,
        pipeline_id: str,
        pipeline_name: str,
        triggered_by: str,
        dag_run_id: str | None = None,
    ) -> Job:
        ts = now()
        record_id = str(uuid.uuid4())
        data = {
            "pipeline_id": pipeline_id,
            "pipeline_name": pipeline_name,
            "status": JobStatus.RUNNING.value,
            "rows_read": 0,
            "rows_written": 0,
            "rows_failed": 0,
            "duration_ms": 0,
            "triggered_by": triggered_by,
            "error": None,
            "log": [],
            "dag_run_id": dag_run_id,
            "started_at": ts.isoformat(),
            "finished_at": None,
            "created_at": ts.isoformat(),
        }
        row = await self._store.create(self.table, record_id, data)
        return self._to_model(row)

    async def update(self, job_id: str, patch: dict[str, Any]) -> Job | None:
        data: dict[str, Any] = {}
        for k, v in patch.items():
            if isinstance(v, datetime):
                data[k] = v.isoformat()
            else:
                data[k] = v
        row = await self._store.update(self.table, job_id, data)
        return self._to_model(row) if row else None

    async def aggregate(self) -> dict[str, int]:
        rows = await self._store.query(
            """
            SELECT
                count() AS jobs,
                count(status = 'succeeded') AS succeeded,
                count(status = 'failed') AS failed,
                math::sum(rows_written) AS rows_written
            FROM job GROUP ALL
            """
        )
        if not rows:
            return {"jobs": 0, "succeeded": 0, "failed": 0, "rows_written": 0}
        r = rows[0]
        return {
            "jobs": int(r.get("jobs") or 0),
            "succeeded": int(r.get("succeeded") or 0),
            "failed": int(r.get("failed") or 0),
            "rows_written": int(r.get("rows_written") or 0),
        }

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _to_model(row: dict[str, Any]) -> Job:
        return Job(
            id=normalise_id(row.get("id")),
            pipeline_id=row.get("pipeline_id", ""),
            pipeline_name=row.get("pipeline_name", ""),
            status=row.get("status") or JobStatus.PENDING.value,
            rows_read=int(row.get("rows_read") or 0),
            rows_written=int(row.get("rows_written") or 0),
            rows_failed=int(row.get("rows_failed") or 0),
            duration_ms=int(row.get("duration_ms") or 0),
            triggered_by=row.get("triggered_by") or "manual",
            error=row.get("error"),
            log=list(row.get("log") or []),
            dag_run_id=row.get("dag_run_id"),
            started_at=coerce_datetime(row.get("started_at")),
            finished_at=coerce_datetime(row.get("finished_at")),
            created_at=coerce_datetime(row.get("created_at")) or now(),
        )
