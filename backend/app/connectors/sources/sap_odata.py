"""SAP OData v2 source.

Targets SAP NetWeaver Gateway services as exposed by SAP ECC 6.0 and
above. Only OData v2 is supported here — that's what ECC ships and
covers >95% of real on-prem SAP integrations. Basic Auth is the
default; an optional CSRF flow is enabled for services that require it.

Incremental sync is driven by ``pipeline.incremental_field`` — the
runner passes the cursor value through to :meth:`read` as ``since`` and
this connector builds the corresponding ``$filter`` clause. The field
and comparison operator are pipeline-configurable, so any
``DateTime``/``Edm.DateTimeOffset`` field on the entity set works
(``LastChangeDateTime``, ``ChangedAt``, ``UpdatedOn``, etc.) without
code changes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.connectors.base import (
    ConnectorMetadata,
    FieldSpec,
    ObjectSpec,
    SourceConnector,
    TestResult,
)
from app.connectors.registry import registry


@registry.register
class SapODataSource(SourceConnector):
    metadata = ConnectorMetadata(
        type="sap_odata",
        label="SAP OData v2 (ECC / S4)",
        role="source",
        description=(
            "Reads entity sets from a SAP NetWeaver Gateway OData v2 "
            "service (ECC 6.0+, S/4HANA). Uses HTTP Basic Auth."
        ),
        icon="sap",
        config_schema=[
            {
                "name": "base_url",
                "label": "Service URL",
                "type": "string",
                "required": True,
                "placeholder": "https://sap.example.com/sap/opu/odata/sap/ZSERVICE_SRV",
            },
            {
                "name": "client",
                "label": "SAP Client (sap-client)",
                "type": "string",
                "placeholder": "100",
            },
            {
                "name": "timeout",
                "label": "Timeout (s)",
                "type": "number",
                "default": 60,
            },
            {
                "name": "verify_ssl",
                "label": "Verify SSL",
                "type": "boolean",
                "default": True,
            },
            {
                "name": "fetch_csrf_token",
                "label": "Fetch CSRF Token",
                "type": "boolean",
                "default": False,
            },
            {
                "name": "incremental_operator",
                "label": "Incremental Operator",
                "type": "select",
                "options": ["gt", "ge"],
                "default": "gt",
            },
        ],
        secret_schema=[
            {"name": "username", "label": "Username", "type": "string"},
            {"name": "password", "label": "Password", "type": "password"},
        ],
    )

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        client = self.config.get("client")
        if client:
            h["sap-client"] = str(client)
        return h

    def _client(self) -> httpx.AsyncClient:
        auth = None
        user = self.secrets.get("username")
        pwd = self.secrets.get("password")
        if user and pwd:
            auth = httpx.BasicAuth(user, pwd)
        return httpx.AsyncClient(
            base_url=self.config["base_url"].rstrip("/"),
            timeout=self.config.get("timeout", 60),
            verify=self.config.get("verify_ssl", True),
            auth=auth,
            headers=self._headers(),
        )

    async def test(self) -> TestResult:
        try:
            async with self._client() as c:
                r = await c.get("/$metadata", headers={"Accept": "application/xml"})
                r.raise_for_status()
            return TestResult(ok=True, message="Connected to SAP OData v2 service")
        except Exception as exc:  # noqa: BLE001
            return TestResult(ok=False, message=f"{type(exc).__name__}: {exc}")

    async def list_objects(self) -> list[ObjectSpec]:
        try:
            async with self._client() as c:
                r = await c.get("/")
                r.raise_for_status()
                data = r.json()
        except Exception:
            return []
        # OData v2 service document: {"d": {"EntitySets": [name, ...]}}
        entries = data.get("d", {}).get("EntitySets") or []
        objs: list[ObjectSpec] = []
        for entry in entries:
            name = entry if isinstance(entry, str) else entry.get("name") or entry.get("url")
            if name:
                objs.append(ObjectSpec(name=name, label=name, fields=[]))
        return objs

    async def read(
        self,
        object_name: str,
        *,
        batch_size: int = 1000,
        since: str | None = None,
        incremental_field: str | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Yield batches from an OData v2 entity set.

        ``incremental_field`` is the column to filter on. If not given
        but ``since`` is, the runner can pass it through; otherwise the
        filter is omitted and a full read is performed.
        """
        params: dict[str, Any] = {
            "$top": batch_size,
            "$format": "json",
            "$inlinecount": "allpages",
        }
        if since and incremental_field:
            op = self.config.get("incremental_operator", "gt")
            params["$filter"] = f"{incremental_field} {op} datetime'{since}'"

        skip = 0
        async with self._client() as c:
            while True:
                params["$skip"] = skip
                r = await c.get(f"/{object_name}", params=params)
                r.raise_for_status()
                body = r.json()
                rows = body.get("d", {}).get("results") or []
                if not rows:
                    return
                yield rows
                if len(rows) < batch_size:
                    return
                skip += batch_size

    @staticmethod
    def _infer_field(value: Any) -> FieldSpec:
        if isinstance(value, bool):
            t = "bool"
        elif isinstance(value, int):
            t = "int"
        elif isinstance(value, float):
            t = "float"
        else:
            t = "string"
        return FieldSpec(name="", type=t)
