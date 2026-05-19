from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Pipeline(BaseModel):
    """One source-object → destination-object materialisation rule."""

    id: str
    name: str
    description: str | None = None
    source_connection_id: str
    destination_connection_id: str
    source_object: str
    destination_object: str
    mode: str = "full"  # full | incremental | upsert
    field_mappings: list[dict[str, Any]] = Field(default_factory=list)
    transform: dict[str, Any] = Field(default_factory=dict)
    schedule: str | None = None  # cron expression
    enabled: bool = True
    incremental_field: str | None = None
    # Columns that uniquely identify a row at the destination. Required
    # for ``mode="upsert"`` against MERGE-capable destinations; ignored
    # otherwise.
    key_columns: list[str] = Field(default_factory=list)
    # "ui" pipelines are editable through the UI; "yaml" pipelines are
    # reloaded from disk and overwrite any manual edits next time the
    # loader runs.
    definition_source: str = "ui"
    definition_path: str | None = None
    created_at: datetime
    updated_at: datetime
