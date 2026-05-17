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
class MssqlDestination(DestinationConnector):
    metadata = ConnectorMetadata(
        type="mssql",
        label="Microsoft SQL Server",
        role="destination",
        description="Writes records to a Microsoft SQL Server table via pyodbc",
        icon="mssql",
        config_schema=[
            {"name": "host", "label": "Host", "type": "string", "required": True},
            {"name": "port", "label": "Port", "type": "number", "default": 1433},
            {"name": "database", "label": "Database", "type": "string", "required": True},
            {"name": "schema", "label": "Schema", "type": "string", "default": "dbo"},
            {"name": "driver", "label": "ODBC Driver", "type": "string",
             "default": "ODBC Driver 18 for SQL Server"},
            {"name": "encrypt", "label": "Encrypt", "type": "boolean", "default": True},
            {"name": "trust_server_certificate", "label": "Trust Server Cert",
             "type": "boolean", "default": False},
        ],
        secret_schema=[
            {"name": "user", "label": "User", "type": "string", "required": True},
            {"name": "password", "label": "Password", "type": "password", "required": True},
        ],
    )

    def _conn_str(self) -> str:
        driver = self.config.get("driver", "ODBC Driver 18 for SQL Server")
        host = self.config["host"]
        port = self.config.get("port", 1433)
        db = self.config["database"]
        encrypt = "yes" if self.config.get("encrypt", True) else "no"
        trust = "yes" if self.config.get("trust_server_certificate", False) else "no"
        return (
            f"DRIVER={{{driver}}};SERVER={host},{port};DATABASE={db};"
            f"UID={self.secrets['user']};PWD={self.secrets['password']};"
            f"Encrypt={encrypt};TrustServerCertificate={trust}"
        )

    def _connect(self):
        import pyodbc

        return pyodbc.connect(self._conn_str())

    async def test(self) -> TestResult:
        def _do() -> TestResult:
            try:
                with self._connect() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.fetchone()
                return TestResult(ok=True, message="Connected to SQL Server")
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
