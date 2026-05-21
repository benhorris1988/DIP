from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_connection_id: Mapped[str] = mapped_column(String(36), index=True)
    destination_connection_id: Mapped[str] = mapped_column(String(36), index=True)
    source_object: Mapped[str] = mapped_column(String(255))
    destination_object: Mapped[str] = mapped_column(String(255))
    mode: Mapped[str] = mapped_column(String(32), default="full")  # full | incremental
    field_mappings: Mapped[list] = mapped_column(JSON, default=list)
    transform: Mapped[dict] = mapped_column(JSON, default=dict)
    schedule: Mapped[str | None] = mapped_column(String(64), nullable=True)  # cron
    enabled: Mapped[bool] = mapped_column(default=True)
    incremental_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Where this pipeline definition came from. "ui" pipelines are editable
    # through the UI; "yaml" pipelines are reloaded from disk and overwrite
    # any manual edits next time the loader runs.
    definition_source: Mapped[str] = mapped_column(String(16), default="ui")
    definition_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
