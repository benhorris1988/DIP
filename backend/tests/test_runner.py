"""End-to-end test of the pipeline runner with fake connectors.

We stand up a real SurrealDB (via the ``surreal_store`` fixture), seed
a source + destination connection, then run a pipeline whose source
and destination are in-memory stubs. This exercises every part of the
runner — connector instantiation, batch loop, mapping, job state
machine, log streaming.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.connectors.base import (
    ConnectorMetadata,
    DestinationConnector,
    ObjectSpec,
    SourceConnector,
    TestResult,
)
from app.connectors.registry import registry
from app.repositories import ConnectionRepository, JobRepository, PipelineRepository
from app.services.runner import run_pipeline

pytestmark = pytest.mark.surreal


class _MemorySource(SourceConnector):
    metadata = ConnectorMetadata(
        type="mem_source",
        label="Memory Source",
        role="source",
        description="test only",
        icon="mem",
        config_schema=[],
        secret_schema=[],
    )

    rows = [
        {"id": 1, "name": "alice"},
        {"id": 2, "name": "bob"},
        {"id": 3, "name": "carol"},
    ]

    async def test(self) -> TestResult:
        return TestResult(ok=True, message="memory")

    async def list_objects(self) -> list[ObjectSpec]:
        return [ObjectSpec(name="people", label="people")]

    async def read(
        self,
        object_name: str,
        *,
        batch_size: int = 1000,
        since: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        yield list(self.rows)


class _MemoryDestination(DestinationConnector):
    metadata = ConnectorMetadata(
        type="mem_dest",
        label="Memory Destination",
        role="destination",
        description="test only",
        icon="mem",
        config_schema=[],
        secret_schema=[],
    )

    storage: list[dict[str, Any]] = []

    async def test(self) -> TestResult:
        return TestResult(ok=True, message="memory")

    async def list_objects(self) -> list[ObjectSpec]:
        return []

    async def write(
        self,
        object_name: str,
        records: list[dict[str, Any]],
        *,
        mode: str = "upsert",
        key_columns: list[str] | None = None,
        **_: Any,
    ) -> int:
        type(self).storage.extend(records)
        return len(records)


@pytest.fixture(autouse=True, scope="module")
def _register_fakes():
    if "mem_source" not in registry._connectors:
        registry.register(_MemorySource)
    if "mem_dest" not in registry._connectors:
        registry.register(_MemoryDestination)
    yield


async def test_run_pipeline_happy_path(surreal_store):
    conns = ConnectionRepository(surreal_store)
    pipes = PipelineRepository(surreal_store)
    jobs = JobRepository(surreal_store)

    _MemoryDestination.storage.clear()
    src = await conns.create(
        name="src", description=None, connector_type="mem_source",
        role="source", config={}, secrets={},
    )
    dst = await conns.create(
        name="dst", description=None, connector_type="mem_dest",
        role="destination", config={}, secrets={},
    )
    p = await pipes.create(
        data={
            "name": "p",
            "source_connection_id": src.id,
            "destination_connection_id": dst.id,
            "source_object": "people",
            "destination_object": "people_out",
            "field_mappings": [
                {"source": "id", "destination": "person_id"},
                {"source": "name", "destination": "full_name"},
            ],
        }
    )

    job = await run_pipeline(surreal_store, p.id, triggered_by="test")
    assert job.status == "succeeded"
    assert job.rows_read == 3
    assert job.rows_written == 3

    persisted = await jobs.get(job.id)
    assert persisted is not None
    assert persisted.status == "succeeded"
    assert persisted.duration_ms >= 0

    # The destination saw the mapped records, not the source records.
    assert _MemoryDestination.storage == [
        {"person_id": 1, "full_name": "alice"},
        {"person_id": 2, "full_name": "bob"},
        {"person_id": 3, "full_name": "carol"},
    ]


async def test_run_pipeline_failure_marks_job(surreal_store):
    conns = ConnectionRepository(surreal_store)
    pipes = PipelineRepository(surreal_store)
    jobs = JobRepository(surreal_store)

    src = await conns.create(
        name="src_f", description=None, connector_type="mem_source",
        role="source", config={}, secrets={},
    )
    dst = await conns.create(
        name="dst_f", description=None, connector_type="mem_dest",
        role="destination", config={}, secrets={},
    )
    p = await pipes.create(
        data={
            "name": "p_fail",
            "source_connection_id": src.id,
            "destination_connection_id": dst.id,
            # Source connector doesn't know this object — but our stub
            # ignores object_name, so simulate failure differently:
            "source_object": "people",
            "destination_object": "people_out",
            # MSSQL-style requirement triggers a ValueError if the
            # destination were mssql; here it's safe.
            "mode": "upsert",
        }
    )

    # Force a failure by monkey-patching the source class to raise.
    import app.connectors.sources.sap_odata as sap_module  # noqa: F401
    original_read = _MemorySource.read

    async def boom(self, *_a, **_k):
        raise RuntimeError("source went bang")
        yield []  # pragma: no cover

    _MemorySource.read = boom  # type: ignore[assignment]
    try:
        job = await run_pipeline(surreal_store, p.id, triggered_by="test")
    finally:
        _MemorySource.read = original_read  # type: ignore[assignment]

    assert job.status == "failed"
    assert job.error and "RuntimeError" in job.error

    persisted = await jobs.get(job.id)
    assert persisted is not None
    assert persisted.status == "failed"
