"""Repositories — typed access to the SurrealDB metadata store.

Each module owns one aggregate (Connection, Pipeline, Job, Asset,
DagRun) and exposes async CRUD + the few list / filter operations the
API and services need. Routes and services depend on these repos, not
on the SurrealDB store directly, so the metadata schema can evolve in
one place.
"""

from app.repositories.asset import AssetMaterializationRepository, AssetRepository
from app.repositories.connection import ConnectionRepository
from app.repositories.dag_run import DagRunRepository
from app.repositories.job import JobRepository
from app.repositories.pipeline import PipelineRepository

__all__ = [
    "AssetMaterializationRepository",
    "AssetRepository",
    "ConnectionRepository",
    "DagRunRepository",
    "JobRepository",
    "PipelineRepository",
]
