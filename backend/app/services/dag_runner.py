"""DAG-aware run orchestrator.

Given a set of target asset keys, computes the upstream closure, plans
the producing pipelines in topological order, and runs them one layer
at a time. A :class:`DagRun` row groups the resulting jobs so the UI
can show "all jobs that ran together."

If any layer fails, downstream layers are skipped — the DagRun ends in
``failed``. Independent assets in the same layer are run sequentially
in v1; parallelism is a future improvement and only safe once we know
two pipelines don't share a destination (or a connection rate-limit).

Progress is published to the SSE bus under ``kind="dag_run"`` so the UI
can stream layer transitions live without polling.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AssetMaterialization, DagRun, Job, JobStatus
from app.services import graph
from app.services.events import bus
from app.services.runner import run_pipeline

logger = logging.getLogger(__name__)


def _snapshot(
    run: DagRun,
    *,
    event: str,
    plan: list[tuple[str, list[str]]] | None = None,
    current_pipeline_id: str | None = None,
    current_assets: list[str] | None = None,
    job_id: str | None = None,
    pipeline_name: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Build an SSE payload describing the current state of a DagRun.

    ``event`` is one of: ``planned``, ``step_started``, ``step_succeeded``,
    ``step_failed``, ``completed``.
    """
    return {
        "id": run.id,
        "event": event,
        "status": run.status,
        "triggered_by": run.triggered_by,
        "requested_assets": list(run.requested_assets or []),
        "resolved_assets": list(run.resolved_assets or []),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "plan": (
            [{"pipeline_id": pid, "assets": keys} for pid, keys in plan]
            if plan is not None
            else None
        ),
        "current_pipeline_id": current_pipeline_id,
        "current_pipeline_name": pipeline_name,
        "current_assets": current_assets,
        "job_id": job_id,
        "error": error,
    }


async def materialize_assets(
    db: AsyncSession,
    asset_keys: list[str],
    *,
    triggered_by: str = "manual",
    include_upstream: bool = True,
) -> DagRun:
    """Materialize ``asset_keys`` and (optionally) everything they depend
    on. Returns the completed :class:`DagRun`."""
    resolved = (
        await graph.upstream_closure(db, asset_keys)
        if include_upstream
        else list(asset_keys)
    )
    plan = await graph.pipelines_for_assets(db, resolved)

    run = DagRun(
        id=str(uuid.uuid4()),
        triggered_by=triggered_by,
        requested_assets=list(asset_keys),
        resolved_assets=list(resolved),
        status=JobStatus.RUNNING.value,
        started_at=datetime.utcnow(),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    await bus.publish(_snapshot(run, event="planned", plan=plan), kind="dag_run")

    failed = False
    last_error: str | None = None
    for pipeline_id, assets_for_pipeline in plan:
        if failed:
            break
        # Look up the pipeline name so SSE consumers don't need a second round-trip.
        pname = None
        from app.models import Pipeline  # local import to avoid circular at module load
        from sqlalchemy import select

        pname_row = (
            await db.execute(select(Pipeline.name).where(Pipeline.id == pipeline_id))
        ).first()
        if pname_row:
            pname = pname_row[0]

        await bus.publish(
            _snapshot(
                run,
                event="step_started",
                current_pipeline_id=pipeline_id,
                current_assets=assets_for_pipeline,
                pipeline_name=pname,
            ),
            kind="dag_run",
        )
        try:
            job: Job = await run_pipeline(
                db, pipeline_id, triggered_by=f"dag:{triggered_by}"
            )
            job.dag_run_id = run.id
            await db.commit()
            if job.status != JobStatus.SUCCEEDED.value:
                failed = True
                last_error = job.error or "pipeline did not succeed"
                await bus.publish(
                    _snapshot(
                        run,
                        event="step_failed",
                        current_pipeline_id=pipeline_id,
                        current_assets=assets_for_pipeline,
                        pipeline_name=pname,
                        job_id=job.id,
                        error=last_error,
                    ),
                    kind="dag_run",
                )
                continue
            for key in assets_for_pipeline:
                db.add(
                    AssetMaterialization(
                        id=str(uuid.uuid4()),
                        asset_key=key,
                        job_id=job.id,
                        pipeline_id=pipeline_id,
                        dag_run_id=run.id,
                        rows_written=job.rows_written,
                    )
                )
            await db.commit()
            await bus.publish(
                _snapshot(
                    run,
                    event="step_succeeded",
                    current_pipeline_id=pipeline_id,
                    current_assets=assets_for_pipeline,
                    pipeline_name=pname,
                    job_id=job.id,
                ),
                kind="dag_run",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("DAG step %s failed", pipeline_id)
            failed = True
            last_error = str(exc)
            await bus.publish(
                _snapshot(
                    run,
                    event="step_failed",
                    current_pipeline_id=pipeline_id,
                    current_assets=assets_for_pipeline,
                    pipeline_name=pname,
                    error=last_error,
                ),
                kind="dag_run",
            )

    run.status = JobStatus.FAILED.value if failed else JobStatus.SUCCEEDED.value
    run.finished_at = datetime.utcnow()
    await db.commit()
    await db.refresh(run)
    await bus.publish(
        _snapshot(run, event="completed", error=last_error),
        kind="dag_run",
    )
    return run
