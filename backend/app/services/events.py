"""In-memory pub/sub bus for streaming entity state changes to SSE
subscribers.

Subscribers get their own ``asyncio.Queue`` so backpressure is
per-listener. Topics are keyed by ``kind`` (``job``, ``dag_run``, …) so
the same bus serves multiple feeds:

* ``{kind}:{id}``  — single entity (Job Detail, DAG Run Detail)
* ``{kind}s:all``  — every entity of that kind (live tiles)

Producers call :meth:`JobEventBus.publish` after every meaningful state
change with a dict payload. Subscribers iterate via
:meth:`JobEventBus.subscribe`.

This bus is in-process; a multi-worker deployment needs Redis pub/sub
or similar — the abstraction here matches that shape so the swap is
local.
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

    def _topics_for(self, kind: str, entity_id: str | None) -> list[str]:
        topics = [f"{kind}s:all"]
        if entity_id:
            topics.append(f"{kind}:{entity_id}")
        return topics

    async def publish(
        self, payload: dict[str, Any], *, kind: str = "job"
    ) -> None:
        for topic in self._topics_for(kind, payload.get("id")):
            for q in list(self._subscribers.get(topic, ())):
                # Drop oldest rather than block a producer on a slow client.
                if q.full():
                    with contextlib.suppress(asyncio.QueueEmpty):
                        q.get_nowait()
                await q.put({"kind": kind, **payload})

    @contextlib.asynccontextmanager
    async def subscribe(
        self,
        *,
        kind: str = "job",
        entity_id: str | None = None,
        job_id: str | None = None,
    ) -> AsyncIterator[asyncio.Queue]:
        # ``job_id`` is the legacy parameter name; preserved so existing
        # callers don't have to change.
        eid = entity_id if entity_id is not None else job_id
        topic = f"{kind}:{eid}" if eid else f"{kind}s:all"
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
        loop.create_task(bus.publish(job_dict, kind="job"))
    except RuntimeError:
        logger.debug("No running loop; dropping job event for %s", job_dict.get("id"))
