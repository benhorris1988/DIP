"""In-memory job event bus.

A lightweight pub/sub for streaming job state changes to SSE subscribers.
Each subscriber gets its own asyncio.Queue so backpressure is per-listener.
Two channels exist:

* ``job:{id}`` — events for a single job, used by Job Detail
* ``jobs:all`` — events for every job, used by the Dashboard live tile

Events are plain dicts shaped like the JobOut schema (or a ``deleted``
sentinel). Producers call :func:`publish_job` after every meaningful
state change; subscribers iterate via :func:`subscribe`.

This bus is in-process; a multi-worker deployment needs Redis pub/sub or
similar — the abstraction here matches that shape so the swap is local.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from typing import Any

logger = logging.getLogger(__name__)


class JobEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}

    def _topics_for(self, job_id: str | None) -> list[str]:
        return ["jobs:all"] + ([f"job:{job_id}"] if job_id else [])

    async def publish(self, job: dict[str, Any]) -> None:
        topics = self._topics_for(job.get("id"))
        for topic in topics:
            for q in list(self._subscribers.get(topic, ())):
                # Best-effort: drop oldest if a slow client is backed up
                if q.full():
                    with contextlib.suppress(asyncio.QueueEmpty):
                        q.get_nowait()
                await q.put(job)

    @contextlib.asynccontextmanager
    async def subscribe(
        self, *, job_id: str | None = None
    ) -> AsyncIterator[asyncio.Queue]:
        topic = f"job:{job_id}" if job_id else "jobs:all"
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._subscribers.setdefault(topic, set()).add(q)
        try:
            yield q
        finally:
            self._subscribers.get(topic, set()).discard(q)


bus = JobEventBus()


def publish_job_sync(job_dict: dict[str, Any]) -> None:
    """Best-effort sync helper for code paths that can't await."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(bus.publish(job_dict))
    except RuntimeError:
        logger.debug("No running loop; dropping job event for %s", job_dict.get("id"))
