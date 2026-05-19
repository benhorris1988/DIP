"""Databricks destination — writes to a Delta table via a SQL Warehouse.

Uses the official ``databricks-sql-connector`` package against a SQL
Warehouse endpoint (HTTP path + workspace host + PAT). The target table
must already exist as a Delta table in the configured catalog.schema; the
connector issues parameterised ``INSERT INTO`` statements with the
warehouse's executemany support.

For richer write semantics (MERGE, partition pruning, CDF) you'd graduate
to Delta Live Tables or the Spark Connect API — out of scope for this
operator console.
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
class DatabricksSqlDestination(DestinationConnector):
    metadata = ConnectorMetadata(
        type="databricks_sql",
        label="Databricks SQL Warehouse",
        role="destination",
        description=(
            "Writes records to a Delta table via a Databricks SQL Warehouse "
            "endpoint"
        ),
        icon="databricks",
        config_schema=[
            {
                "name": "server_hostname",
                "label": "Workspace hostname",
                "type": "string",
                "required": True,
                "help_text": "e.g. dbc-abc123.cloud.databricks.com",
            },
            {
                "name": "http_path",
                "label": "HTTP path",
                "type": "string",
                "required": True,
                "help_text": "e.g. /sql/1.0/warehouses/abcdef123456",
            },
            {"name": "catalog", "label": "Catalog", "type": "string", "default": "main"},
            {"name": "schema", "label": "Schema", "type": "string", "default": "default"},
        ],
        secret_schema=[
            {
                "name": "access_token",
                "label": "Personal access token",
                "type": "password",
                "required": True,
            },
        ],
    )

    def _connect(self):
        from databricks import sql

        return sql.connect(
            server_hostname=self.config["server_hostname"],
            http_path=self.config["http_path"],
            access_token=self.secrets["access_token"],
            catalog=self.config.get("catalog", "main"),
            schema=self.config.get("schema", "default"),
        )

    async def test(self) -> TestResult:
        def _do() -> TestResult:
            try:
                with self._connect() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.fetchone()
                return TestResult(ok=True, message="Connected to Databricks SQL Warehouse")
            except Exception as exc:  # noqa: BLE001
                return TestResult(ok=False, message=f"{type(exc).__name__}: {exc}")

        return await asyncio.to_thread(_do)

    async def list_objects(self) -> list[ObjectSpec]:
        def _do() -> list[ObjectSpec]:
            catalog = self.config.get("catalog", "main")
            schema = self.config.get("schema", "default")
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SHOW TABLES IN `%s`.`%s`" % (catalog, schema)
                )
                # Result columns vary; the table name is generally column 1 or 'tableName'
                rows = cur.fetchall()
                names: list[str] = []
                for row in rows:
                    name = None
                    try:
                        name = row["tableName"]  # type: ignore[index]
                    except Exception:  # noqa: BLE001
                        name = row[1] if len(row) > 1 else row[0]
                    if name:
                        names.append(str(name))
                return [ObjectSpec(name=n, label=n) for n in names]

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
        key_columns: list[str] | None = None,
        **_: Any,
    ) -> int:
        if not records:
            return 0
        catalog = self.config.get("catalog", "main")
        schema = self.config.get("schema", "default")
        qualified = f"`{catalog}`.`{schema}`.`{object_name}`"
        cols = list(records[0].keys())
        placeholders = ",".join("?" for _ in cols)
        col_list = ",".join(f"`{c}`" for c in cols)
        sql_text = f"INSERT INTO {qualified} ({col_list}) VALUES ({placeholders})"

        def _do() -> int:
            with self._connect() as conn:
                cur = conn.cursor()
                cur.executemany(sql_text, [[r.get(c) for c in cols] for r in records])
                conn.commit()
                return len(records)

        return await asyncio.to_thread(_do)
