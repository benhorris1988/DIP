from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Connection, Job, JobStatus, Pipeline
from app.schemas.job import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
async def list_jobs(
    pipeline_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[Job]:
    stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
    if pipeline_id:
        stmt = stmt.where(Job.pipeline_id == pipeline_id)
    if status:
        stmt = stmt.where(Job.status == status)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)) -> dict:
    total_pipelines = (await db.execute(select(func.count(Pipeline.id)))).scalar_one()
    total_connections = (await db.execute(select(func.count(Connection.id)))).scalar_one()
    total_jobs = (await db.execute(select(func.count(Job.id)))).scalar_one()
    succeeded = (
        await db.execute(
            select(func.count(Job.id)).where(Job.status == JobStatus.SUCCEEDED.value)
        )
    ).scalar_one()
    failed = (
        await db.execute(
            select(func.count(Job.id)).where(Job.status == JobStatus.FAILED.value)
        )
    ).scalar_one()
    rows_written = (await db.execute(select(func.coalesce(func.sum(Job.rows_written), 0)))).scalar_one()
    return {
        "pipelines": total_pipelines,
        "connections": total_connections,
        "jobs": total_jobs,
        "succeeded": succeeded,
        "failed": failed,
        "rows_written": rows_written,
    }


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)) -> Job:
    obj = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Job not found")
    return obj
