"""DAG-aware run orchestrator.

Given a set of target asset keys, computes the upstream closure, plans
the producing pipelines in topological order, and runs them one layer
at a time. A :class:`DagRun` row groups the resulting jobs so the UI
can show "all jobs that ran together."

If any layer fails, downstream layers are skipped — the DagRun ends in
``failed``. Independent assets in the same layer are run sequentially
in v1; parallelism is a future improvement and only safe once we know
two pipelines don't share a destination (or a connection rate-limit).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AssetMaterialization, DagRun, Job, JobStatus
from app.services import graph
from app.services.runner import run_pipeline

logger = logging.getLogger(__name__)


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

    failed = False
    for pipeline_id, assets_for_pipeline in plan:
        if failed:
            break
        try:
            job: Job = await run_pipeline(
                db, pipeline_id, triggered_by=f"dag:{triggered_by}"
            )
            job.dag_run_id = run.id
            await db.commit()
            if job.status != JobStatus.SUCCEEDED.value:
                failed = True
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
        except Exception:  # noqa: BLE001
            logger.exception("DAG step %s failed", pipeline_id)
            failed = True

    run.status = JobStatus.FAILED.value if failed else JobStatus.SUCCEEDED.value
    run.finished_at = datetime.utcnow()
    await db.commit()
    await db.refresh(run)
    return run


