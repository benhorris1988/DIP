"""Smoke tests for the FastAPI routes against a real SurrealDB.

These exercise the JSON contracts the Flutter client depends on — if
field names or status codes regress, these blow up.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    assets,
    connections,
    connectors,
    dag_runs,
    definitions,
    jobs,
    pipelines,
)

pytestmark = pytest.mark.surreal


def _app() -> FastAPI:
    app = FastAPI(title="dip-test")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(connectors.router, prefix="/api")
    app.include_router(connections.router, prefix="/api")
    app.include_router(pipelines.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(assets.router, prefix="/api")
    app.include_router(dag_runs.router, prefix="/api")
    app.include_router(definitions.router, prefix="/api")
    return app


@pytest.fixture
async def client(surreal_store):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app()), base_url="http://test"
    ) as c:
        yield c


async def test_list_connectors(client):
    r = await client.get("/api/connectors")
    assert r.status_code == 200
    types = {c["type"] for c in r.json()}
    # The built-in connectors should always be present.
    assert {"sap_odata", "oracle", "surrealdb", "mssql"}.issubset(types)


async def test_connection_lifecycle(client):
    payload = {
        "name": "sap_test",
        "description": None,
        "connector_type": "sap_odata",
        "role": "source",
        "config": {"base_url": "https://sap.example.com/srv"},
        "secrets": {"username": "u", "password": "p"},
    }
    r = await client.post("/api/connections", json=payload)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    r = await client.get("/api/connections")
    assert r.status_code == 200
    assert any(c["id"] == cid for c in r.json())

    r = await client.post("/api/connections", json=payload)
    assert r.status_code == 409  # duplicate name

    r = await client.delete(f"/api/connections/{cid}")
    assert r.status_code == 204


async def test_pipeline_create_validates_roles(client):
    src_payload = {
        "name": "src",
        "connector_type": "sap_odata",
        "role": "source",
        "config": {"base_url": "x"},
        "secrets": {},
    }
    dst_payload = {
        "name": "dst",
        "connector_type": "mssql",
        "role": "destination",
        "config": {"host": "h", "database": "d"},
        "secrets": {"user": "u", "password": "p"},
    }
    src = (await client.post("/api/connections", json=src_payload)).json()
    dst = (await client.post("/api/connections", json=dst_payload)).json()

    good = {
        "name": "p1",
        "source_connection_id": src["id"],
        "destination_connection_id": dst["id"],
        "source_object": "BusinessPartner",
        "destination_object": "dim_customer",
        "mode": "upsert",
        "key_columns": ["customer_key"],
        "schedule": "0 */4 * * *",
        "enabled": True,
        "field_mappings": [
            {"source": "BusinessPartner", "destination": "customer_key"},
        ],
    }
    r = await client.post("/api/pipelines", json=good)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["key_columns"] == ["customer_key"]
    assert body["schedule"] == "0 */4 * * *"

    # Swapping roles should be rejected.
    bad = dict(good)
    bad["name"] = "p2"
    bad["source_connection_id"] = dst["id"]  # destination used as source
    bad["destination_connection_id"] = src["id"]
    r = await client.post("/api/pipelines", json=bad)
    assert r.status_code == 400


async def test_jobs_stats_zeroes_on_fresh_db(client):
    r = await client.get("/api/jobs/stats")
    assert r.status_code == 200
    body = r.json()
    for key in ("pipelines", "connections", "jobs", "succeeded", "failed", "rows_written"):
        assert key in body
        assert body[key] >= 0
