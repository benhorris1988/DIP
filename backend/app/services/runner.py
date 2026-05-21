from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import registry
from app.connectors.base import DestinationConnector, SourceConnector
from app.models import Asset, AssetMaterialization, Connection, Job, JobStatus, Pipeline
from app.schemas.job import JobOut
from app.services.events import bus

logger = logging.getLogger(__name__)


def _apply_mapping(record: dict, mappings: list[dict]) -> dict:
    if not mappings:
        return record
    out: dict = {}
    for m in mappings:
        src = m.get("source")
        dst = m.get("destination")
        if src and dst and src in record:
            out[dst] = record[src]
    return out


def _snapshot(job: Job) -> dict:
    return JobOut.model_validate(job).model_dump(mode="json")


async def _publish(job: Job) -> None:
    try:
        await bus.publish(_snapshot(job))
    except Exception:  # noqa: BLE001
        logger.debug("Failed to publish job event", exc_info=True)


async def run_pipeline(
    db: AsyncSession, pipeline_id: str, *, triggered_by: str = "manual"
) -> Job:
    pipeline = (await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))).scalar_one()

    src_conn = (
        await db.execute(select(Connection).where(Connection.id == pipeline.source_connection_id))
    ).scalar_one()
    dst_conn = (
        await db.execute(
            select(Connection).where(Connection.id == pipeline.destination_connection_id)
        )
    ).scalar_one()

    job = Job(
        id=str(uuid.uuid4()),
        pipeline_id=pipeline.id,
        pipeline_name=pipeline.name,
        status=JobStatus.RUNNING.value,
        triggered_by=triggered_by,
        started_at=datetime.utcnow(),
        log=[],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    await _publish(job)

    log: list[dict] = []

    async def _log(msg: str, level: str = "info") -> None:
        log.append({"ts": datetime.utcnow().isoformat(), "level": level, "message": msg})
        # Snapshot the in-progress log so subscribers see streamed updates
        job.log = list(log)
        await _publish(job)

    started = time.monotonic()
    rows_read = 0
    rows_written = 0
    try:
        source: SourceConnector = registry.instance(  # type: ignore[assignment]
            src_conn.connector_type, src_conn.config, src_conn.secrets
        )
        destination: DestinationConnector = registry.instance(  # type: ignore[assignment]
            dst_conn.connector_type, dst_conn.config, dst_conn.secrets
        )
        await _log(
            f"Starting {pipeline.name}: "
            f"{src_conn.connector_type}:{pipeline.source_object} -> "
            f"{dst_conn.connector_type}:{pipeline.destination_object}"
        )

        mappings = pipeline.field_mappings or []
        async for batch in source.read(pipeline.source_object, batch_size=500):
            rows_read += len(batch)
            mapped = [_apply_mapping(r, mappings) for r in batch] if mappings else batch
            written = await destination.write(
                pipeline.destination_object, mapped, mode="upsert"
            )
            rows_written += written
            # Update counters before logging so the event payload is consistent
            job.rows_read = rows_read
            job.rows_written = rows_written
            await _log(f"Batch processed: read={len(batch)} written={written}")

        job.status = JobStatus.SUCCEEDED.value
        await _log("Pipeline completed successfully")
        # Record asset materializations for any assets produced by this
        # pipeline. DAG-driven runs do this themselves to attach a
        # ``dag_run_id``; the no-op here is harmless.
        if job.dag_run_id is None:
            assets = (
                await db.execute(select(Asset).where(Asset.pipeline_id == pipeline.id))
            ).scalars().all()
            for a in assets:
                db.add(
                    AssetMaterialization(
                        id=str(uuid.uuid4()),
                        asset_key=a.key,
                        job_id=job.id,
                        pipeline_id=pipeline.id,
                        rows_written=rows_written,
                    )
                )
    except Exception as exc:  # noqa: BLE001
        job.status = JobStatus.FAILED.value
        job.error = f"{type(exc).__name__}: {exc}"
        await _log(job.error, level="error")
        logger.exception("Pipeline %s failed", pipeline.name)
    finally:
        job.rows_read = rows_read
        job.rows_written = rows_written
        job.duration_ms = int((time.monotonic() - started) * 1000)
        job.finished_at = datetime.utcnow()
        job.log = log
        await db.commit()
        await db.refresh(job)
        await _publish(job)
    return job
