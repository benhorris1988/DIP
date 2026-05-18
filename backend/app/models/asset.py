from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Asset(Base):
    """A data product. Identified by a stable key (e.g. ``dim_customer``).

    Each asset is materialized by exactly one pipeline (its producer) and
    can declare a list of upstream asset keys it depends on. The asset
    graph is the DAG over these ``depends_on`` edges.
    """

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pipeline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
    # Physical location of the materialized asset. Optional — some assets
    # may be virtual (e.g. computed in-place during a downstream pipeline).
    connection_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    object_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    depends_on: Mapped[list] = mapped_column(JSON, default=list)
    # Free-form metadata declared in YAML: owner, tier, group, tags, …
    asset_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    definition_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class AssetMaterialization(Base):
    """A point-in-time record that an asset was produced by a job."""

    __tablename__ = "asset_materializations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_key: Mapped[str] = mapped_column(String(255), index=True)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    pipeline_id: Mapped[str] = mapped_column(String(36), index=True)
    dag_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    rows_written: Mapped[int] = mapped_column(Integer, default=0)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DagRun(Base):
    """Wraps N jobs that ran together as part of a single asset
    materialization graph."""

    __tablename__ = "dag_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    triggered_by: Mapped[str] = mapped_column(String(32), default="manual")
    requested_assets: Mapped[list] = mapped_column(JSON, default=list)
    resolved_assets: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
