"""Tests for the cron-driven pipeline scheduler.

We don't need a real SurrealDB for these — the scheduler logic only
talks to repositories through ``PipelineRepository.list_enabled_with_schedule``,
which we can fake with a tiny stub. That keeps the cron-evaluation
logic isolated from the rest of the system.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytest

import app.services.scheduler as scheduler


@dataclass
class _StubPipeline:
    id: str
    name: str
    schedule: str | None
    enabled: bool = True


class _StubStore:
    def __init__(self, pipelines: list[_StubPipeline]) -> None:
        self._pipelines = pipelines


class _StubPipelineRepo:
    def __init__(self, store: _StubStore) -> None:
        self._store = store

    async def list_enabled_with_schedule(self) -> list[_StubPipeline]:
        return [p for p in self._store._pipelines if p.enabled and p.schedule]


@pytest.fixture
def patched(monkeypatch):
    monkeypatch.setattr(scheduler, "PipelineRepository", _StubPipelineRepo)
    return scheduler


async def test_due_pipelines_fires_when_cron_matches(patched):
    store = _StubStore([_StubPipeline(id="1", name="hourly", schedule="0 * * * *")])
    # 12:00:30 UTC — top of the hour, the "0 * * * *" cron is due.
    due = await patched._due_pipelines(store, datetime(2026, 5, 19, 12, 0, 30))
    assert [p.name for p in due] == ["hourly"]


async def test_due_pipelines_skips_when_cron_not_due(patched):
    store = _StubStore([_StubPipeline(id="1", name="hourly", schedule="0 * * * *")])
    # 12:30 UTC — the next "0 * * * *" fire is at 13:00, not due now.
    due = await patched._due_pipelines(store, datetime(2026, 5, 19, 12, 30, 0))
    assert due == []


async def test_due_pipelines_ignores_invalid_cron(patched, caplog):
    store = _StubStore([_StubPipeline(id="1", name="bad", schedule="not-a-cron")])
    due = await patched._due_pipelines(store, datetime(2026, 5, 19, 12, 0, 0))
    assert due == []


async def test_due_pipelines_skips_disabled(patched):
    store = _StubStore(
        [_StubPipeline(id="1", name="off", schedule="* * * * *", enabled=False)]
    )
    # list_enabled_with_schedule filters disabled ones out before we evaluate.
    due = await patched._due_pipelines(store, datetime(2026, 5, 19, 12, 0, 0))
    assert due == []


def test_policy_to_seconds_prefers_shorter_window():
    assert scheduler._policy_to_seconds({"max_age_minutes": 30}) == 30 * 60
    assert scheduler._policy_to_seconds({"max_age_hours": 2}) == 2 * 3600
    # Both set → shorter wins (30 minutes < 2 hours).
    assert scheduler._policy_to_seconds(
        {"max_age_minutes": 30, "max_age_hours": 2}
    ) == 30 * 60
    assert scheduler._policy_to_seconds({}) is None


def test_policy_to_seconds_ignores_invalid():
    assert scheduler._policy_to_seconds({"max_age_minutes": 0}) is None
    assert scheduler._policy_to_seconds({"max_age_minutes": -5}) is None
    assert scheduler._policy_to_seconds({"max_age_hours": "abc"}) is None  # type: ignore[arg-type]
