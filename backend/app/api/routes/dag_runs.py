from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import AssetMaterialization, DagRun, Job
from app.services.events import bus

router = APIRouter(prefix="/dag-runs", tags=["dag-runs"])


def _sse_event(payload: dict, event: str = "dag_run") -> bytes:
    body = json.dumps(payload, default=str)
    return f"event: {event}\ndata: {body}\n\n".encode()


async def _sse_iter(request: Request, run_id: str | None) -> AsyncIterator[bytes]:
    yield b": connected\n\n"
    async with bus.subscribe(kind="dag_run", entity_id=run_id) as queue:
        while True:
            if await request.is_disconnected():
                return
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=15)
                yield _sse_event(payload)
            except asyncio.TimeoutError:
                yield b": keep-alive\n\n"


@router.get("/stream")
async def stream_all(request: Request) -> StreamingResponse:
    """SSE: every DAG run state change, for the Dashboard / Assets page."""
    return StreamingResponse(
        _sse_iter(request, None),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{run_id}/stream")
async def stream_one(run_id: str, request: Request) -> StreamingResponse:
    """SSE: events for a single DAG run, for the DAG Run Detail page."""
    return StreamingResponse(
        _sse_iter(request, run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("")
async def list_runs(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        await db.execute(
            select(DagRun).order_by(desc(DagRun.started_at)).limit(limit)
        )
    ).scalars().all()
    return [
        {
            "id": r.id,
            "triggered_by": r.triggered_by,
            "status": r.status,
            "requested_assets": list(r.requested_assets or []),
            "resolved_assets": list(r.resolved_assets or []),
            "started_at": r.started_at,
            "finished_at": r.finished_at,
        }
        for r in rows
    ]


@router.get("/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    run = (
        await db.execute(select(DagRun).where(DagRun.id == run_id))
    ).scalar_one_or_none()
    if not run:
        raise HTTPException(404, "DAG run not found")
    jobs = (
        await db.execute(
            select(Job).where(Job.dag_run_id == run.id).order_by(Job.created_at)
        )
    ).scalars().all()
    mats = (
        await db.execute(
            select(AssetMaterialization).where(
                AssetMaterialization.dag_run_id == run.id
            )
        )
    ).scalars().all()
    return {
        "id": run.id,
        "triggered_by": run.triggered_by,
        "status": run.status,
        "requested_assets": list(run.requested_assets or []),
        "resolved_assets": list(run.resolved_assets or []),
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "jobs": [
            {
                "id": j.id,
                "pipeline_id": j.pipeline_id,
                "pipeline_name": j.pipeline_name,
                "status": j.status,
                "rows_read": j.rows_read,
                "rows_written": j.rows_written,
                "error": j.error,
                "started_at": j.started_at,
                "finished_at": j.finished_at,
            }
            for j in jobs
        ],
        "materializations": [
            {
                "asset_key": m.asset_key,
                "job_id": m.job_id,
                "rows_written": m.rows_written,
                "ts": m.ts,
            }
            for m in mats
        ],
    }
