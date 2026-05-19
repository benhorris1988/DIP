from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from app.connectors import registry
from app.connectors.base import DestinationConnector, SourceConnector
from app.db.surreal import SurrealStore
from app.models import Job, JobStatus, Pipeline
from app.repositories import (
    AssetMaterializationRepository,
    AssetRepository,
    ConnectionRepository,
    JobRepository,
    PipelineRepository,
)
from app.repositories._common import now
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
    return JobOut.model_validate(job, from_attributes=True).model_dump(mode="json")


async def _publish(job: Job) -> None:
    try:
        await bus.publish(_snapshot(job))
    except Exception:  # noqa: BLE001
        logger.debug("Failed to publish job event", exc_info=True)


def _materialization_kwargs(pipeline: Pipeline) -> dict[str, Any]:
    """Extra args passed to destination.write() for MERGE-capable destinations.

    We surface ``key_columns`` (defined on the Pipeline so a pipeline
    operator can change them without touching connector config) and the
    pipeline-level ``mode``. Connectors that don't understand these keys
    accept ``**kwargs`` and ignore them.
    """
    return {
        "key_columns": list(pipeline.key_columns or []),
        "mode": pipeline.mode if pipeline.mode in {"insert", "upsert"} else "upsert",
    }


async def run_pipeline(
    store: SurrealStore,
    pipeline_id: str,
    *,
    triggered_by: str = "manual",
) -> Job:
    pipelines = PipelineRepository(store)
    connections = ConnectionRepository(store)
    jobs = JobRepository(store)
    assets_repo = AssetRepository(store)
    mats_repo = AssetMaterializationRepository(store)

    pipeline = await pipelines.get(pipeline_id)
    if pipeline is None:
        raise LookupError(f"pipeline {pipeline_id} not found")
    src_conn = await connections.get(pipeline.source_connection_id)
    dst_conn = await connections.get(pipeline.destination_connection_id)
    if src_conn is None or dst_conn is None:
        raise LookupError("source or destination connection missing")

    job = await jobs.create(
        pipeline_id=pipeline.id,
        pipeline_name=pipeline.name,
        triggered_by=triggered_by,
    )
    await _publish(job)

    log: list[dict] = []

    async def _log(msg: str, level: str = "info") -> None:
        log.append({"ts": datetime.utcnow().isoformat(), "level": level, "message": msg})
        job.log = list(log)
        await jobs.update(job.id, {"log": list(log)})
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
        write_kwargs = _materialization_kwargs(pipeline)
        read_kwargs: dict[str, Any] = {"batch_size": 500}
        if pipeline.incremental_field:
            read_kwargs["incremental_field"] = pipeline.incremental_field
        async for batch in source.read(pipeline.source_object, **read_kwargs):
            rows_read += len(batch)
            mapped = [_apply_mapping(r, mappings) for r in batch] if mappings else batch
            written = await destination.write(
                pipeline.destination_object,
                mapped,
                **write_kwargs,
            )
            rows_written += written
            job.rows_read = rows_read
            job.rows_written = rows_written
            await jobs.update(
                job.id, {"rows_read": rows_read, "rows_written": rows_written}
            )
            await _log(f"Batch processed: read={len(batch)} written={written}")

        job.status = JobStatus.SUCCEEDED.value
        await _log("Pipeline completed successfully")
        # Record asset materializations for assets produced by this pipeline.
        # DAG-driven runs attach their own ``dag_run_id`` later.
        if job.dag_run_id is None:
            assets = await assets_repo.list_for_pipeline(pipeline.id)
            for a in assets:
                await mats_repo.record(
                    asset_key=a.key,
                    job_id=job.id,
                    pipeline_id=pipeline.id,
                    rows_written=rows_written,
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
        job.finished_at = now()
        job.log = log
        await jobs.update(
            job.id,
            {
                "status": job.status,
                "rows_read": rows_read,
                "rows_written": rows_written,
                "duration_ms": job.duration_ms,
                "finished_at": job.finished_at,
                "error": job.error,
                "log": log,
            },
        )
        await _publish(job)
    return job
