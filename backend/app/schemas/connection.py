from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConnectionBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    connector_type: str
    role: str
    config: dict[str, Any] = Field(default_factory=dict)


class ConnectionCreate(ConnectionBase):
    secrets: dict[str, Any] = Field(default_factory=dict)


class ConnectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    secrets: dict[str, Any] | None = None


class ConnectionOut(ConnectionBase):
    id: str
    status: str
    last_tested_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
