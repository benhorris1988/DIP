"""Microsoft Fabric Warehouse destination.

Targets the TDS endpoint of a Fabric Warehouse — same wire protocol as
SQL Server but with Entra ID (Azure AD) authentication. Supports two
auth modes via the ``auth`` config field:

* ``sql``  — username + password (DB users created inside the Warehouse)
* ``spn``  — service principal: tenant + client_id + client_secret

The Warehouse must already exist; this connector does *not* create the
warehouse itself, only writes to a table inside it.

Future work: a ``fabric_lakehouse`` sibling connector that writes Parquet
to OneLake via the DFS endpoint (needs pyarrow + azure-identity).
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.connectors.base import (
    ConnectorMetadata,
    DestinationConnector,
    ObjectSpec,
    TestResult,
)
from app.connectors.registry import registry


@registry.register
class FabricWarehouseDestination(DestinationConnector):
    metadata = ConnectorMetadata(
        type="fabric_warehouse",
        label="Microsoft Fabric Warehouse",
        role="destination",
        description=(
            "Writes records to a Microsoft Fabric Warehouse via the TDS "
            "endpoint with Entra ID authentication"
        ),
        icon="fabric",
        config_schema=[
            {
                "name": "endpoint",
                "label": "Warehouse endpoint",
                "type": "string",
                "required": True,
                "help_text": (
                    "Connection string host, e.g. "
                    "abcd1234.datawarehouse.fabric.microsoft.com"
                ),
            },
            {"name": "database", "label": "Warehouse name", "type": "string", "required": True},
            {"name": "schema", "label": "Schema", "type": "string", "default": "dbo"},
            {
                "name": "driver",
                "label": "ODBC Driver",
                "type": "string",
                "default": "ODBC Driver 18 for SQL Server",
            },
            {
                "name": "auth",
                "label": "Auth mode",
                "type": "string",
                "options": ["sql", "spn"],
                "default": "spn",
            },
        ],
        secret_schema=[
            # Used when auth = "sql"
            {"name": "user", "label": "User (SQL auth)", "type": "string"},
            {"name": "password", "label": "Password (SQL auth)", "type": "password"},
            # Used when auth = "spn"
            {"name": "tenant_id", "label": "Tenant ID (SPN)", "type": "string"},
            {"name": "client_id", "label": "Client ID (SPN)", "type": "string"},
            {"name": "client_secret", "label": "Client secret (SPN)", "type": "password"},
        ],
    )

    def _conn_str(self) -> str:
        driver = self.config.get("driver", "ODBC Driver 18 for SQL Server")
        endpoint = self.config["endpoint"]
        db = self.config["database"]
        base = (
            f"DRIVER={{{driver}}};SERVER={endpoint};DATABASE={db};"
            "Encrypt=yes;TrustServerCertificate=no;"
        )
        auth = self.config.get("auth", "spn")
        if auth == "sql":
            user = self.secrets.get("user", "")
            password = self.secrets.get("password", "")
            return base + f"UID={user};PWD={password};"
        # Service principal — pyodbc understands this token type
        return (
            base
            + "Authentication=ActiveDirectoryServicePrincipal;"
            + f"UID={self.secrets.get('client_id', '')};"
            + f"PWD={self.secrets.get('client_secret', '')};"
            + f"Authority Id={self.secrets.get('tenant_id', '')};"
        )

    def _connect(self):
        import pyodbc

        return pyodbc.connect(self._conn_str(), timeout=30)

    async def test(self) -> TestResult:
        def _do() -> TestResult:
            try:
                with self._connect() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.fetchone()
                return TestResult(ok=True, message="Connected to Fabric Warehouse")
            except Exception as exc:  # noqa: BLE001
                return TestResult(ok=False, message=f"{type(exc).__name__}: {exc}")

        return await asyncio.to_thread(_do)

    async def list_objects(self) -> list[ObjectSpec]:
        def _do() -> list[ObjectSpec]:
            schema = self.config.get("schema", "dbo")
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = ? ORDER BY table_name",
                    schema,
                )
                return [ObjectSpec(name=r[0], label=r[0]) for r in cur.fetchall()]

        try:
            return await asyncio.to_thread(_do)
        except Exception:
            return []

    async def write(
        self,
        object_name: str,
        records: list[dict[str, Any]],
        *,
        mode: str = "upsert",
    ) -> int:
        if not records:
            return 0
        schema = self.config.get("schema", "dbo")
        qualified = f"[{schema}].[{object_name}]"
        cols = list(records[0].keys())
        placeholders = ",".join("?" for _ in cols)
        col_list = ",".join(f"[{c}]" for c in cols)
        sql = f"INSERT INTO {qualified} ({col_list}) VALUES ({placeholders})"

        def _do() -> int:
            with self._connect() as conn:
                cur = conn.cursor()
                cur.fast_executemany = True
                cur.executemany(sql, [[r.get(c) for c in cols] for r in records])
                conn.commit()
                return len(records)

        return await asyncio.to_thread(_do)
