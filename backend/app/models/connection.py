from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Connection(BaseModel):
    """A configured link to an external source or destination system."""

    id: str
    name: str
    description: str | None = None
    connector_type: str
    role: str  # "source" | "destination"
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, Any] = Field(default_factory=dict)
    status: str = "unknown"
    last_tested_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
