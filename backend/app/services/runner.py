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
from app.services.transforms import apply_transforms

logger = logging.getLogger(__name__)

# Cap how many distinct error samples we keep on a job's log so a pathological
# batch can't blow up the JSON column.
MAX_LOGGED_ERRORS = 25


def _mapping_transform(value, transform: str | None):
    if not transform or value is None:
        return value
    op = transform.strip().lower()
    if op == "upper":
        return str(value).upper()
    if op == "lower":
        return str(value).lower()
    if op == "trim":
        return str(value).strip()
    return value


def _apply_mapping(record: dict, mappings: list[dict]) -> dict:
    if not mappings:
        return record
    out: dict = {}
    for m in mappings:
        src = m.get("source")
        dst = m.get("destination")
        if src and dst and src in record:
            out[dst] = _mapping_transform(record[src], m.get("transform"))
    return out


async def _write_batch(
    destination: DestinationConnector,
    object_name: str,
    records: list[dict],
    *,
    on_error: str,
) -> tuple[int, int, list[str]]:
    """Write a batch, returning ``(written, failed, error_samples)``.

    On ``on_error='skip'`` a batch write that raises is retried row-by-row so
    a single bad record doesn't sink the whole batch — the offending rows are
    counted as failed and skipped. On ``on_error='fail'`` the exception
    propagates and the run fails.
    """
    if not records:
        return 0, 0, []
    try:
        written = await destination.write(object_name, records, mode="upsert")
        return written, 0, []
    except Exception:  # noqa: BLE001
        if on_error == "fail":
            raise
    written = 0
    failed = 0
    errors: list[str] = []
    for record in records:
        try:
            written += await destination.write(object_name, [record], mode="upsert")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            if len(errors) < 5:
                errors.append(f"{type(exc).__name__}: {exc}")
    return written, failed, errors


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
    rows_failed = 0
    rows_filtered = 0
    logged_errors = 0
    transform_cfg = pipeline.transform or {}
    steps = transform_cfg.get("steps") or []
    on_error = transform_cfg.get("on_error", "skip")
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
        if steps:
            await _log(
                f"Transform plan: {len(steps)} step(s), on_error={on_error}"
            )

        mappings = pipeline.field_mappings or []
        async for batch in source.read(pipeline.source_object, batch_size=500):
            rows_read += len(batch)
            mapped = [_apply_mapping(r, mappings) for r in batch] if mappings else batch

            # Apply the transformation steps (cast / python / filter / …).
            # A TransformError (on_error=fail, or invalid config) propagates to
            # the outer handler and fails the whole run.
            if steps:
                outcome = apply_transforms(mapped, steps, on_error=on_error)
                mapped = outcome.records
                rows_failed += outcome.failed
                rows_filtered += outcome.filtered
                for err in outcome.errors:
                    if logged_errors >= MAX_LOGGED_ERRORS:
                        break
                    logged_errors += 1
                    await _log(
                        f"Transform error (row {err['row_index']}): {err['error']}",
                        level="error",
                    )

            written, write_failed, write_errors = await _write_batch(
                destination,
                pipeline.destination_object,
                mapped,
                on_error=on_error,
            )
            rows_written += written
            rows_failed += write_failed
            for werr in write_errors:
                if logged_errors >= MAX_LOGGED_ERRORS:
                    break
                logged_errors += 1
                await _log(f"Write error: {werr}", level="error")
            # Update counters before logging so the event payload is consistent
            job.rows_read = rows_read
            job.rows_written = rows_written
            job.rows_failed = rows_failed
            msg = f"Batch processed: read={len(batch)} written={written}"
            if write_failed:
                msg += f" failed={write_failed}"
            await _log(msg)

        job.status = JobStatus.SUCCEEDED.value
        summary = f"Pipeline completed: {rows_written} written"
        if rows_failed:
            summary += f", {rows_failed} failed"
        if rows_filtered:
            summary += f", {rows_filtered} filtered out"
        await _log(summary, level="warn" if rows_failed else "info")
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
        job.rows_failed = rows_failed
        job.duration_ms = int((time.monotonic() - started) * 1000)
        job.finished_at = datetime.utcnow()
        job.log = log
        await db.commit()
        await db.refresh(job)
        await _publish(job)
    return job
