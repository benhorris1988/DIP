from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from app.connectors.base import (
    ConnectorMetadata,
    FieldSpec,
    ObjectSpec,
    SourceConnector,
    TestResult,
)
from app.connectors.registry import registry

_SQL_TYPE_MAP = {
    "int": "int",
    "bigint": "int",
    "smallint": "int",
    "tinyint": "int",
    "bit": "bool",
    "decimal": "float",
    "numeric": "float",
    "money": "float",
    "float": "float",
    "real": "float",
    "date": "datetime",
    "datetime": "datetime",
    "datetime2": "datetime",
    "smalldatetime": "datetime",
    "datetimeoffset": "datetime",
}


@registry.register
class MssqlSource(SourceConnector):
    metadata = ConnectorMetadata(
        type="mssql_source",
        label="Microsoft SQL Server",
        role="source",
        description="Reads tables from a Microsoft SQL Server database via pyodbc",
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
            {"name": "incremental_column", "label": "Incremental Column (optional)",
             "type": "string",
             "placeholder": "ModifiedDate",
             "help_text": "High-watermark column used when a run supplies a 'since' value."},
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
                    "SELECT table_name, column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_schema = ? "
                    "ORDER BY table_name, ordinal_position",
                    schema,
                )
                by_table: dict[str, list[FieldSpec]] = {}
                for table, column, data_type, nullable in cur.fetchall():
                    by_table.setdefault(table, []).append(
                        FieldSpec(
                            name=column,
                            type=_SQL_TYPE_MAP.get((data_type or "").lower(), "string"),
                            nullable=(nullable == "YES"),
                        )
                    )
                return [
                    ObjectSpec(name=t, label=t, fields=fields)
                    for t, fields in by_table.items()
                ]

        try:
            return await asyncio.to_thread(_do)
        except Exception:
            return []

    async def read(
        self, object_name: str, *, batch_size: int = 1000, since: str | None = None
    ) -> AsyncIterator[list[dict[str, Any]]]:
        schema = self.config.get("schema", "dbo")
        qualified = f"[{schema}].[{object_name}]"
        watermark = self.config.get("incremental_column")
        where = ""
        params: list[Any] = []
        if since and watermark:
            where = f" WHERE [{watermark}] > ?"
            params.append(since)

        def _fetch_all() -> tuple[list[str], list[tuple]]:
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute(f"SELECT * FROM {qualified}{where}", *params)
                cols = [d[0] for d in cur.description]
                rows: list[tuple] = []
                while True:
                    chunk = cur.fetchmany(batch_size)
                    if not chunk:
                        break
                    rows.extend(chunk)
                return cols, rows

        cols, rows = await asyncio.to_thread(_fetch_all)
        for start in range(0, len(rows), batch_size):
            chunk = rows[start : start + batch_size]
            yield [dict(zip(cols, r, strict=False)) for r in chunk]
