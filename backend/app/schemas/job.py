from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobOut(BaseModel):
    id: str
    pipeline_id: str
    pipeline_name: str
    status: str
    rows_read: int
    rows_written: int
    rows_failed: int
    duration_ms: int
    triggered_by: str
    error: str | None
    log: list[Any]
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
