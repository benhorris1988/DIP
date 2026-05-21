"""Background scheduling.

Two cooperating jobs run on a single APScheduler ``AsyncIOScheduler``:

1. **cron_tick** — every minute, fires any pipeline whose ``schedule``
   cron expression matches the current minute. Pipelines disabled in
   the UI (or by YAML) are skipped.

2. **freshness_tick** — every ``settings.freshness_check_interval_seconds``,
   inspects every asset with a ``freshness_policy``. If the asset's
   most recent successful materialization is older than the policy
   allows (or the asset has never been materialized), the
   auto-materializer schedules a DAG run for it.

To avoid materialization storms, the auto-materializer:

* skips assets that already have a DagRun in ``running`` state
  covering them in ``resolved_assets``;
* groups all stale assets into a *single* DAG run per tick, so the
  upstream closure is computed once and shared dependencies don't run
  twice;
* tags the DagRun with ``triggered_by="auto"`` so operators can tell
  human-initiated runs apart in the UI.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import async_session
from app.models import Asset, AssetMaterialization, DagRun, JobStatus, Pipeline
from app.services.dag_runner import materialize_assets
from app.services.runner import run_pipeline

logger = logging.getLogger(__name__)

# Module-level singleton so ``start_scheduler`` and ``stop_scheduler`` can
# be called from FastAPI's lifespan without leaking state across tests.
_scheduler: AsyncIOScheduler | None = None


async def _due_pipelines(db: AsyncSession, now: datetime) -> list[Pipeline]:
    """Return enabled pipelines whose cron schedule fires at ``now``.

    We compare ``CronTrigger.get_next_fire_time`` taken from one minute
    ago — if that next fire is within the current minute window, it's
    due. This avoids drift even if the scheduler tick is slightly late.
    """
    pipelines = (
        await db.execute(
            select(Pipeline).where(
                Pipeline.enabled.is_(True), Pipeline.schedule.is_not(None)
            )
        )
    ).scalars().all()
    due: list[Pipeline] = []
    one_min_ago = now - timedelta(minutes=1)
    for p in pipelines:
        if not p.schedule:
            continue
        try:
            trigger = CronTrigger.from_crontab(p.schedule)
        except ValueError:
            logger.warning("pipeline %s has invalid cron %r", p.name, p.schedule)
            continue
        next_fire = trigger.get_next_fire_time(None, one_min_ago)
        if next_fire is not None and next_fire <= now:
            due.append(p)
    return due


async def cron_tick() -> None:
    """Fire any pipeline whose cron schedule is due this minute."""
    now = datetime.utcnow()
    async with async_session() as db:
        due = await _due_pipelines(db, now)
        for p in due:
            logger.info("cron_tick: firing %s (%s)", p.name, p.schedule)
            try:
                await run_pipeline(db, p.id, triggered_by="cron")
            except Exception:  # noqa: BLE001
                logger.exception("cron_tick: %s failed", p.name)


async def _stale_assets(db: AsyncSession, now: datetime) -> list[Asset]:
    """Assets whose freshness policy says they should be re-materialised."""
    assets = (
        await db.execute(
            select(Asset).where(Asset.freshness_policy != {})  # type: ignore[arg-type]
        )
    ).scalars().all()

    if not assets:
        return []

    # Pull the most recent materialization per asset in a single query.
    rows = (
        await db.execute(
            select(AssetMaterialization).order_by(desc(AssetMaterialization.ts))
        )
    ).scalars().all()
    last_ts: dict[str, datetime] = {}
    for row in rows:
        last_ts.setdefault(row.asset_key, row.ts)

    stale: list[Asset] = []
    for a in assets:
        max_age_seconds = _policy_to_seconds(a.freshness_policy or {})
        if max_age_seconds is None:
            continue
        last = last_ts.get(a.key)
        if last is None or (now - last).total_seconds() >= max_age_seconds:
            stale.append(a)
    return stale


def _policy_to_seconds(policy: dict) -> int | None:
    """Convert a stored freshness policy dict to a max-age in seconds.

    Mirrors :class:`FreshnessSpec.to_max_age_seconds` but operates on the
    serialised dict the loader writes, so the scheduler doesn't have to
    import the loader. Whichever bound is shorter wins.
    """
    candidates: list[int] = []
    minutes = policy.get("max_age_minutes")
    hours = policy.get("max_age_hours")
    if isinstance(minutes, int) and minutes > 0:
        candidates.append(minutes * 60)
    if isinstance(hours, (int, float)) and hours > 0:
        candidates.append(int(hours * 3600))
    return min(candidates) if candidates else None


async def _already_in_flight(
    db: AsyncSession, keys: list[str]
) -> set[str]:
    """Return the subset of ``keys`` already covered by a running DagRun."""
    if not keys:
        return set()
    runs = (
        await db.execute(
            select(DagRun).where(DagRun.status == JobStatus.RUNNING.value)
        )
    ).scalars().all()
    covered: set[str] = set()
    for r in runs:
        covered.update(r.resolved_assets or [])
    return {k for k in keys if k in covered}


async def freshness_tick() -> None:
    """Check freshness policies and auto-materialize anything stale."""
    now = datetime.utcnow()
    async with async_session() as db:
        stale = await _stale_assets(db, now)
        if not stale:
            return
        keys = [a.key for a in stale]
        in_flight = await _already_in_flight(db, keys)
        eligible = [k for k in keys if k not in in_flight]
        if not eligible:
            logger.debug("freshness_tick: all stale assets already running")
            return
        logger.info("freshness_tick: materializing %d stale asset(s): %s",
                    len(eligible), ", ".join(eligible))
        try:
            await materialize_assets(
                db,
                eligible,
                triggered_by="auto",
                include_upstream=True,
            )
        except Exception:  # noqa: BLE001
            logger.exception("freshness_tick: materialization failed")


def start_scheduler() -> AsyncIOScheduler | None:
    """Initialise APScheduler with our two recurring jobs.

    Returns the live scheduler instance, or ``None`` if scheduling is
    disabled in settings. Safe to call again — calling while a scheduler
    is already running is a no-op.
    """
    global _scheduler
    settings = get_settings()
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled (DIP_SCHEDULER_ENABLED=false)")
        return None
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        cron_tick,
        trigger="interval",
        seconds=60,
        id="cron_tick",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        freshness_tick,
        trigger="interval",
        seconds=settings.freshness_check_interval_seconds,
        id="freshness_tick",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started: cron every 60s, freshness every %ds",
        settings.freshness_check_interval_seconds,
    )
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
