"""Tests for the SAP OData v2 source connector.

We mock the network with ``httpx.MockTransport`` so the tests don't
need a real SAP system.
"""

from __future__ import annotations

import httpx
import pytest

from app.connectors.sources.sap_odata import SapODataSource


def _make_source(handler, **config_overrides):
    """Build a SapODataSource whose httpx client uses a mock transport."""
    cfg = {"base_url": "https://sap.example.com/srv", "timeout": 5, "verify_ssl": False}
    cfg.update(config_overrides)
    src = SapODataSource(config=cfg, secrets={"username": "u", "password": "p"})

    def _client():
        return httpx.AsyncClient(
            base_url=cfg["base_url"].rstrip("/"),
            transport=httpx.MockTransport(handler),
            auth=httpx.BasicAuth("u", "p"),
            headers={"Accept": "application/json"},
        )

    src._client = _client  # type: ignore[method-assign]
    return src


async def test_test_method_pings_metadata():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, text="<edmx/>")

    src = _make_source(handler)
    result = await src.test()
    assert result.ok is True
    assert calls[0].endswith("/$metadata")


async def test_read_full_paginates_until_short_batch():
    requested: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(dict(request.url.params))
        skip = int(request.url.params.get("$skip", "0"))
        # First page: full batch. Second page: short batch — terminates.
        if skip == 0:
            return httpx.Response(
                200, json={"d": {"results": [{"id": i} for i in range(3)]}}
            )
        return httpx.Response(200, json={"d": {"results": [{"id": 99}]}})

    src = _make_source(handler)
    batches = []
    async for batch in src.read("BusinessPartner", batch_size=3):
        batches.append(batch)
    assert [len(b) for b in batches] == [3, 1]
    # No filter on a full read.
    assert "$filter" not in requested[0]


async def test_read_incremental_uses_field_and_operator():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url.params.get("$filter", ""))
        return httpx.Response(200, json={"d": {"results": []}})

    src = _make_source(handler, incremental_operator="ge")
    async for _ in src.read(
        "BusinessPartner",
        batch_size=10,
        since="2025-05-01T00:00:00",
        incremental_field="LastChangeDateTime",
    ):
        pass
    assert captured[0] == "LastChangeDateTime ge datetime'2025-05-01T00:00:00'"


async def test_read_omits_filter_when_field_missing():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url.params.get("$filter", ""))
        return httpx.Response(200, json={"d": {"results": []}})

    src = _make_source(handler)
    # Caller passed since= but no incremental_field — nothing to filter on.
    async for _ in src.read("X", since="2025-01-01"):
        pass
    assert captured[0] == ""


async def test_list_objects_reads_service_document():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/"):
            return httpx.Response(
                200,
                json={
                    "d": {
                        "EntitySets": ["BusinessPartner", "SalesOrder", "Material"]
                    }
                },
            )
        return httpx.Response(404)

    src = _make_source(handler)
    objs = await src.list_objects()
    assert [o.name for o in objs] == ["BusinessPartner", "SalesOrder", "Material"]


async def test_sap_client_header_propagates():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("sap-client", ""))
        return httpx.Response(200, json={"d": {"results": []}})

    cfg = {
        "base_url": "https://sap.example.com/srv",
        "client": "100",
        "verify_ssl": False,
        "timeout": 5,
    }
    src = SapODataSource(config=cfg, secrets={"username": "u", "password": "p"})

    def _client():
        return httpx.AsyncClient(
            base_url=cfg["base_url"].rstrip("/"),
            transport=httpx.MockTransport(handler),
            auth=httpx.BasicAuth("u", "p"),
            headers=src._headers(),
        )

    src._client = _client  # type: ignore[method-assign]
    async for _ in src.read("BusinessPartner"):
        pass
    assert seen and seen[0] == "100"


def test_metadata_advertises_only_v2():
    meta = SapODataSource.metadata
    assert meta.type == "sap_odata"
    names = [f["name"] for f in meta.config_schema]
    # OData version is no longer a config knob — v2 is the only supported mode.
    assert "odata_version" not in names
    assert "incremental_operator" in names
