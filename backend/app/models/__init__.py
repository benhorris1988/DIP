"""Domain models, as plain pydantic objects.

These models describe the shape of records stored in the SurrealDB
metadata store. They are deliberately lightweight — there's no ORM,
no session lifecycle, just typed dataclass-like containers that the
repository layer turns into SurrealQL queries.
"""

from app.models.asset import Asset, AssetMaterialization, DagRun
from app.models.connection import Connection
from app.models.job import Job, JobStatus
from app.models.pipeline import Pipeline

__all__ = [
    "Asset",
    "AssetMaterialization",
    "Connection",
    "DagRun",
    "Job",
    "JobStatus",
    "Pipeline",
]
