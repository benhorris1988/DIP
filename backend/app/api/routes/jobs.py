from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.db.surreal import SurrealStore, get_store
from app.repositories import ConnectionRepository, JobRepository, PipelineRepository
from app.schemas.job import JobOut
from app.services.events import bus

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _repo(store: SurrealStore = Depends(get_store)) -> JobRepository:
    return JobRepository(store)


@router.get("", response_model=list[JobOut])
async def list_jobs(
    pipeline_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    repo: JobRepository = Depends(_repo),
) -> list[JobOut]:
    items = await repo.list(pipeline_id=pipeline_id, status=status, limit=limit)
    return [JobOut.model_validate(i, from_attributes=True) for i in items]


@router.get("/stats")
async def stats(store: SurrealStore = Depends(get_store)) -> dict:
    jobs = JobRepository(store)
    pipelines = PipelineRepository(store)
    connections = ConnectionRepository(store)

    agg = await jobs.aggregate()
    total_pipelines = await pipelines.count()
    total_connections = len(await connections.list())
    return {
        "pipelines": total_pipelines,
        "connections": total_connections,
        "jobs": agg["jobs"],
        "succeeded": agg["succeeded"],
        "failed": agg["failed"],
        "rows_written": agg["rows_written"],
    }


# ---------------------------------------------------------------------------
# SSE endpoints — declared before ``/{job_id}`` so paths don't collide
# ---------------------------------------------------------------------------


def _sse_event(payload: dict, event: str = "job") -> bytes:
    body = json.dumps(payload, default=str)
    return f"event: {event}\ndata: {body}\n\n".encode()


async def _sse_iter(
    request: Request, job_id: str | None
) -> AsyncIterator[bytes]:
    yield b": connected\n\n"
    async with bus.subscribe(job_id=job_id) as queue:
        while True:
            if await request.is_disconnected():
                return
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=15)
                yield _sse_event(payload)
            except asyncio.TimeoutError:
                yield b": keep-alive\n\n"


@router.get("/stream")
async def stream_all_jobs(request: Request) -> StreamingResponse:
    """SSE: all job state changes, for the Dashboard live tile."""
    return StreamingResponse(
        _sse_iter(request, None),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{job_id}/stream")
async def stream_one_job(job_id: str, request: Request) -> StreamingResponse:
    """SSE: events for a single job, for the Job Detail page."""
    return StreamingResponse(
        _sse_iter(request, job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, repo: JobRepository = Depends(_repo)) -> JobOut:
    obj = await repo.get(job_id)
    if not obj:
        raise HTTPException(404, "Job not found")
    return JobOut.model_validate(obj, from_attributes=True)
