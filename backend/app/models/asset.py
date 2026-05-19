from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Asset(BaseModel):
    """A data product. Identified by a stable key (e.g. ``dim_customer``).

    Each asset is materialized by exactly one pipeline (its producer)
    and can declare a list of upstream asset keys it depends on. The
    asset graph is the DAG over these ``depends_on`` edges.
    """

    id: str
    key: str
    description: str | None = None
    pipeline_id: str
    connection_id: str | None = None
    object_name: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    asset_metadata: dict[str, Any] = Field(default_factory=dict)
    freshness_policy: dict[str, Any] = Field(default_factory=dict)
    definition_path: str | None = None
    created_at: datetime
    updated_at: datetime


class AssetMaterialization(BaseModel):
    """A point-in-time record that an asset was produced by a job."""

    id: str
    asset_key: str
    job_id: str
    pipeline_id: str
    dag_run_id: str | None = None
    rows_written: int = 0
    ts: datetime


class DagRun(BaseModel):
    """Wraps N jobs that ran together as part of a single materialization graph."""

    id: str
    triggered_by: str = "manual"
    requested_assets: list[str] = Field(default_factory=list)
    resolved_assets: list[str] = Field(default_factory=list)
    status: str = "running"
    started_at: datetime
    finished_at: datetime | None = None
