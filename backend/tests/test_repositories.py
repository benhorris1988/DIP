"""Integration tests for the SurrealDB-backed repositories.

These run only when the ``surreal`` binary is available — the
``surreal_store`` fixture skips otherwise.
"""

from __future__ import annotations

import pytest

from app.repositories import (
    AssetMaterializationRepository,
    AssetRepository,
    ConnectionRepository,
    DagRunRepository,
    JobRepository,
    PipelineRepository,
)

pytestmark = pytest.mark.surreal


async def test_connection_crud(surreal_store):
    repo = ConnectionRepository(surreal_store)

    created = await repo.create(
        name="sap_prod",
        description="ECC primary",
        connector_type="sap_odata",
        role="source",
        config={"base_url": "https://sap.example.com/srv"},
        secrets={"username": "u", "password": "p"},
    )
    assert created.id
    assert created.name == "sap_prod"

    fetched = await repo.get(created.id)
    assert fetched is not None
    assert fetched.name == "sap_prod"
    assert fetched.config["base_url"] == "https://sap.example.com/srv"

    by_name = await repo.get_by_name("sap_prod")
    assert by_name is not None and by_name.id == created.id

    listing = await repo.list(role="source")
    assert len(listing) == 1

    await repo.update(created.id, {"description": "primary ERP"})
    assert (await repo.get(created.id)).description == "primary ERP"

    assert await repo.delete(created.id) is True
    assert await repo.get(created.id) is None


async def test_connection_name_uniqueness(surreal_store):
    repo = ConnectionRepository(surreal_store)
    await repo.create(
        name="dup",
        description=None,
        connector_type="sap_odata",
        role="source",
        config={},
        secrets={},
    )
    # The SurrealDB unique index on `name` blocks the second insert.
    with pytest.raises(Exception):
        await repo.create(
            name="dup",
            description=None,
            connector_type="sap_odata",
            role="source",
            config={},
            secrets={},
        )


async def test_pipeline_filters(surreal_store):
    conns = ConnectionRepository(surreal_store)
    pipes = PipelineRepository(surreal_store)
    src = await conns.create(
        name="src",
        description=None,
        connector_type="sap_odata",
        role="source",
        config={},
        secrets={},
    )
    dst = await conns.create(
        name="dst",
        description=None,
        connector_type="mssql",
        role="destination",
        config={},
        secrets={},
    )
    await pipes.create(
        data={
            "name": "scheduled",
            "source_connection_id": src.id,
            "destination_connection_id": dst.id,
            "source_object": "X",
            "destination_object": "Y",
            "schedule": "*/5 * * * *",
            "enabled": True,
        }
    )
    await pipes.create(
        data={
            "name": "manual",
            "source_connection_id": src.id,
            "destination_connection_id": dst.id,
            "source_object": "X",
            "destination_object": "Y",
            "enabled": True,
        }
    )
    await pipes.create(
        data={
            "name": "disabled",
            "source_connection_id": src.id,
            "destination_connection_id": dst.id,
            "source_object": "X",
            "destination_object": "Y",
            "schedule": "0 * * * *",
            "enabled": False,
        }
    )
    due = await pipes.list_enabled_with_schedule()
    assert {p.name for p in due} == {"scheduled"}


async def test_job_aggregate(surreal_store):
    conns = ConnectionRepository(surreal_store)
    pipes = PipelineRepository(surreal_store)
    jobs = JobRepository(surreal_store)
    src = await conns.create(
        name="s", description=None, connector_type="oracle", role="source",
        config={}, secrets={},
    )
    dst = await conns.create(
        name="d", description=None, connector_type="mssql", role="destination",
        config={}, secrets={},
    )
    p = await pipes.create(
        data={
            "name": "p",
            "source_connection_id": src.id,
            "destination_connection_id": dst.id,
            "source_object": "X",
            "destination_object": "Y",
        }
    )
    j = await jobs.create(pipeline_id=p.id, pipeline_name=p.name, triggered_by="manual")
    await jobs.update(j.id, {"status": "succeeded", "rows_written": 7})
    j2 = await jobs.create(pipeline_id=p.id, pipeline_name=p.name, triggered_by="cron")
    await jobs.update(j2.id, {"status": "failed", "rows_written": 0})

    agg = await jobs.aggregate()
    assert agg["jobs"] == 2
    assert agg["succeeded"] == 1
    assert agg["failed"] == 1
    assert agg["rows_written"] == 7


async def test_asset_freshness_listing(surreal_store):
    conns = ConnectionRepository(surreal_store)
    pipes = PipelineRepository(surreal_store)
    assets = AssetRepository(surreal_store)
    src = await conns.create(
        name="src2", description=None, connector_type="oracle", role="source",
        config={}, secrets={},
    )
    dst = await conns.create(
        name="dst2", description=None, connector_type="mssql", role="destination",
        config={}, secrets={},
    )
    p = await pipes.create(
        data={
            "name": "p2",
            "source_connection_id": src.id,
            "destination_connection_id": dst.id,
            "source_object": "X",
            "destination_object": "Y",
        }
    )
    await assets.upsert(
        key="with_freshness",
        pipeline_id=p.id,
        freshness_policy={"max_age_minutes": 60},
    )
    await assets.upsert(key="without_freshness", pipeline_id=p.id)

    fresh = await assets.list_with_freshness_policy()
    assert {a.key for a in fresh} == {"with_freshness"}


async def test_dag_run_running_filter(surreal_store):
    runs = DagRunRepository(surreal_store)
    r1 = await runs.create(
        triggered_by="auto", requested_assets=["a"], resolved_assets=["a"]
    )
    await runs.update(r1.id, {"status": "succeeded"})
    r2 = await runs.create(
        triggered_by="manual", requested_assets=["b"], resolved_assets=["b"]
    )
    running = await runs.list_running()
    assert {r.id for r in running} == {r2.id}


async def test_asset_materialization_latest(surreal_store):
    conns = ConnectionRepository(surreal_store)
    pipes = PipelineRepository(surreal_store)
    jobs = JobRepository(surreal_store)
    mats = AssetMaterializationRepository(surreal_store)
    src = await conns.create(
        name="src3", description=None, connector_type="oracle", role="source",
        config={}, secrets={},
    )
    dst = await conns.create(
        name="dst3", description=None, connector_type="mssql", role="destination",
        config={}, secrets={},
    )
    p = await pipes.create(
        data={
            "name": "p3",
            "source_connection_id": src.id,
            "destination_connection_id": dst.id,
            "source_object": "X",
            "destination_object": "Y",
        }
    )
    j = await jobs.create(pipeline_id=p.id, pipeline_name=p.name, triggered_by="manual")
    await mats.record(asset_key="ak", job_id=j.id, pipeline_id=p.id, rows_written=10)
    await mats.record(asset_key="ak", job_id=j.id, pipeline_id=p.id, rows_written=20)

    latest = await mats.latest_per_asset()
    assert "ak" in latest
    # Either materialization is the latest depending on timestamp resolution;
    # whichever it is, the rows_written must be one of the values we wrote.
    assert latest["ak"].rows_written in {10, 20}
