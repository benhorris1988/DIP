from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AssetOut(BaseModel):
    id: str
    key: str
    description: str | None
    pipeline_id: str
    connection_id: str | None
    object_name: str | None
    depends_on: list[str]
    asset_metadata: dict[str, Any]
    definition_path: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssetWithStatus(AssetOut):
    pipeline_name: str | None = None
    last_materialized_at: datetime | None = None
    last_job_id: str | None = None
    last_status: str | None = None
    rows_written: int | None = None


class AssetMaterializationOut(BaseModel):
    id: str
    asset_key: str
    job_id: str
    pipeline_id: str
    dag_run_id: str | None
    rows_written: int
    ts: datetime

    class Config:
        from_attributes = True


class AssetGraph(BaseModel):
    layers: list[list[str]]
    nodes: list[AssetWithStatus]


class DagRunOut(BaseModel):
    id: str
    triggered_by: str
    status: str
    requested_assets: list[str]
    resolved_assets: list[str]
    started_at: datetime
    finished_at: datetime | None

    class Config:
        from_attributes = True


class MaterializeRequest(BaseModel):
    keys: list[str]
    include_upstream: bool = True
