from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(BaseModel):
    id: str
    pipeline_id: str
    pipeline_name: str
    status: str = JobStatus.PENDING.value
    rows_read: int = 0
    rows_written: int = 0
    rows_failed: int = 0
    duration_ms: int = 0
    triggered_by: str = "manual"
    error: str | None = None
    log: list[dict[str, Any]] = Field(default_factory=list)
    dag_run_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
