"""Microsoft SQL Server destination.

Writes via pyodbc. Two modes are supported:

* ``mode="insert"`` — plain ``INSERT … (cols) VALUES (?…)`` with
  ``fast_executemany`` for bulk speed.
* ``mode="upsert"`` — a single set-based ``MERGE`` per batch:
  rows are loaded into a session-scoped staging table with
  ``fast_executemany``, then ``MERGE target USING #stage ON <key>
  WHEN MATCHED UPDATE WHEN NOT MATCHED INSERT`` collapses the
  staging table into the target in one statement.

At ~40k rows/hour the MERGE path is essentially free on the server —
work is dominated by the network round-trip for the bulk insert, not
by the MERGE itself. The staging table is dropped automatically when
the connection closes (it's a ``#temp`` table).

The set of ``key_columns`` comes from the pipeline definition so an
operator can change it without touching connector config.
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
class MssqlDestination(DestinationConnector):
    metadata = ConnectorMetadata(
        type="mssql",
        label="Microsoft SQL Server",
        role="destination",
        description="Writes records to Microsoft SQL Server via pyodbc, with MERGE-based upserts",
        icon="mssql",
        config_schema=[
            {"name": "host", "label": "Host", "type": "string", "required": True},
            {"name": "port", "label": "Port", "type": "number", "default": 1433},
            {"name": "database", "label": "Database", "type": "string", "required": True},
            {"name": "schema", "label": "Schema", "type": "string", "default": "dbo"},
            {
                "name": "driver",
                "label": "ODBC Driver",
                "type": "string",
                "default": "ODBC Driver 18 for SQL Server",
            },
            {"name": "encrypt", "label": "Encrypt", "type": "boolean", "default": True},
            {
                "name": "trust_server_certificate",
                "label": "Trust Server Cert",
                "type": "boolean",
                "default": False,
            },
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
        key_columns: list[str] | None = None,
        **_: Any,
    ) -> int:
        if not records:
            return 0
        schema = self.config.get("schema", "dbo")
        cols = list(records[0].keys())
        if mode == "upsert":
            keys = list(key_columns or [])
            if not keys:
                raise ValueError(
                    "mssql upsert requires key_columns on the pipeline; "
                    "set Pipeline.key_columns or use mode='insert'."
                )
            missing = [k for k in keys if k not in cols]
            if missing:
                raise ValueError(
                    f"key_columns {missing!r} not present in mapped record columns {cols!r}"
                )
            return await asyncio.to_thread(self._merge, schema, object_name, cols, keys, records)
        return await asyncio.to_thread(self._insert, schema, object_name, cols, records)

    # ------------------------------------------------------------------
    # Sync implementations (run on a worker thread)
    # ------------------------------------------------------------------

    def _insert(
        self,
        schema: str,
        table: str,
        cols: list[str],
        records: list[dict[str, Any]],
    ) -> int:
        qualified = f"[{schema}].[{table}]"
        placeholders = ",".join("?" for _ in cols)
        col_list = ",".join(f"[{c}]" for c in cols)
        sql = f"INSERT INTO {qualified} ({col_list}) VALUES ({placeholders})"
        with self._connect() as conn:
            cur = conn.cursor()
            cur.fast_executemany = True
            cur.executemany(sql, [[r.get(c) for c in cols] for r in records])
            conn.commit()
            return len(records)

    def _merge(
        self,
        schema: str,
        table: str,
        cols: list[str],
        keys: list[str],
        records: list[dict[str, Any]],
    ) -> int:
        """Stage the batch in ``#dip_stage`` and MERGE into the target.

        The staging table mirrors the target's column types via
        ``SELECT TOP 0`` so we don't have to introspect schemas. One
        round-trip uploads the batch via ``fast_executemany``; the
        MERGE statement collapses it into the target in a single set
        operation.
        """
        qualified = f"[{schema}].[{table}]"
        col_list = ",".join(f"[{c}]" for c in cols)
        placeholders = ",".join("?" for _ in cols)
        non_keys = [c for c in cols if c not in keys]

        on_clause = " AND ".join(f"tgt.[{k}] = src.[{k}]" for k in keys)
        if non_keys:
            set_clause = ", ".join(f"tgt.[{c}] = src.[{c}]" for c in non_keys)
            matched_clause = f"WHEN MATCHED THEN UPDATE SET {set_clause}"
        else:
            # All columns are keys → nothing to update on match.
            matched_clause = ""
        insert_cols = col_list
        insert_vals = ",".join(f"src.[{c}]" for c in cols)
        merge_sql = (
            f"MERGE {qualified} AS tgt "
            f"USING #dip_stage AS src "
            f"ON {on_clause} "
            f"{matched_clause} "
            f"WHEN NOT MATCHED BY TARGET THEN "
            f"  INSERT ({insert_cols}) VALUES ({insert_vals});"
        )

        with self._connect() as conn:
            cur = conn.cursor()
            cur.fast_executemany = True
            # Stage with the target's exact types — survives the connection.
            cur.execute(f"SELECT TOP 0 {col_list} INTO #dip_stage FROM {qualified};")
            cur.execute("TRUNCATE TABLE #dip_stage;")
            cur.executemany(
                f"INSERT INTO #dip_stage ({col_list}) VALUES ({placeholders})",
                [[r.get(c) for c in cols] for r in records],
            )
            cur.execute(merge_sql)
            conn.commit()
            return len(records)


def build_merge_sql(
    *,
    schema: str,
    table: str,
    cols: list[str],
    keys: list[str],
) -> str:
    """Pure helper used by the test suite to assert the SQL shape.

    Mirrors :meth:`MssqlDestination._merge` exactly — kept as a free
    function so tests don't need a live ODBC driver.
    """
    qualified = f"[{schema}].[{table}]"
    col_list = ",".join(f"[{c}]" for c in cols)
    non_keys = [c for c in cols if c not in keys]
    on_clause = " AND ".join(f"tgt.[{k}] = src.[{k}]" for k in keys)
    if non_keys:
        set_clause = ", ".join(f"tgt.[{c}] = src.[{c}]" for c in non_keys)
        matched_clause = f"WHEN MATCHED THEN UPDATE SET {set_clause}"
    else:
        matched_clause = ""
    insert_vals = ",".join(f"src.[{c}]" for c in cols)
    return (
        f"MERGE {qualified} AS tgt "
        f"USING #dip_stage AS src "
        f"ON {on_clause} "
        f"{matched_clause} "
        f"WHEN NOT MATCHED BY TARGET THEN "
        f"  INSERT ({col_list}) VALUES ({insert_vals});"
    )
