from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FieldMapping(BaseModel):
    source: str
    destination: str
    transform: str | None = None  # optional expression


class PipelineBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    source_connection_id: str
    destination_connection_id: str
    source_object: str
    destination_object: str
    mode: str = "full"
    field_mappings: list[FieldMapping] = Field(default_factory=list)
    transform: dict[str, Any] = Field(default_factory=dict)
    schedule: str | None = None
    enabled: bool = True


class PipelineCreate(PipelineBase):
    pass


class PipelineUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    source_object: str | None = None
    destination_object: str | None = None
    mode: str | None = None
    field_mappings: list[FieldMapping] | None = None
    transform: dict[str, Any] | None = None
    schedule: str | None = None
    enabled: bool | None = None


class PipelineOut(PipelineBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
