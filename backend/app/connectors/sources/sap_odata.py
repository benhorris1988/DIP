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
        label="SAP OData",
        role="source",
        description="Reads entity sets from a SAP OData v2/v4 service",
        icon="sap",
        config_schema=[
            {"name": "base_url", "label": "Service URL", "type": "string", "required": True,
             "placeholder": "https://sap.example.com/sap/opu/odata/sap/ZSERVICE_SRV"},
            {"name": "odata_version", "label": "OData Version", "type": "select",
             "options": ["v2", "v4"], "default": "v2"},
            {"name": "timeout", "label": "Timeout (s)", "type": "number", "default": 30},
            {"name": "verify_ssl", "label": "Verify SSL", "type": "boolean", "default": True},
        ],
        secret_schema=[
            {"name": "username", "label": "Username", "type": "string"},
            {"name": "password", "label": "Password", "type": "password"},
        ],
    )

    def _client(self) -> httpx.AsyncClient:
        auth = None
        user = self.secrets.get("username")
        pwd = self.secrets.get("password")
        if user and pwd:
            auth = httpx.BasicAuth(user, pwd)
        return httpx.AsyncClient(
            base_url=self.config["base_url"].rstrip("/"),
            timeout=self.config.get("timeout", 30),
            verify=self.config.get("verify_ssl", True),
            auth=auth,
            headers={"Accept": "application/json"},
        )

    async def test(self) -> TestResult:
        try:
            async with self._client() as c:
                r = await c.get("/$metadata", headers={"Accept": "application/xml"})
                r.raise_for_status()
            return TestResult(ok=True, message="Connected to SAP OData service")
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
        entries = data.get("d", {}).get("EntitySets") or data.get("value") or []
        objs: list[ObjectSpec] = []
        for entry in entries:
            name = entry if isinstance(entry, str) else entry.get("name") or entry.get("url")
            if name:
                objs.append(ObjectSpec(name=name, label=name, fields=[]))
        return objs

    async def read(
        self, object_name: str, *, batch_size: int = 1000, since: str | None = None
    ) -> AsyncIterator[list[dict[str, Any]]]:
        version = self.config.get("odata_version", "v2")
        params: dict[str, Any] = {"$top": batch_size}
        if version == "v2":
            params["$format"] = "json"
            params["$inlinecount"] = "allpages"
        else:
            params["$count"] = "true"
        if since:
            params["$filter"] = f"LastModified gt {since}"

        skip = 0
        async with self._client() as c:
            while True:
                params["$skip"] = skip
                r = await c.get(f"/{object_name}", params=params)
                r.raise_for_status()
                body = r.json()
                rows = (
                    body.get("d", {}).get("results")
                    if version == "v2"
                    else body.get("value")
                ) or []
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
