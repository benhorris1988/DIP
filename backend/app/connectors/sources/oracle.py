from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from app.connectors.base import (
    ConnectorMetadata,
    ObjectSpec,
    SourceConnector,
    TestResult,
)
from app.connectors.registry import registry


@registry.register
class OracleSource(SourceConnector):
    metadata = ConnectorMetadata(
        type="oracle",
        label="Oracle Database",
        role="source",
        description="Reads tables from Oracle Database via python-oracledb (thin mode)",
        icon="oracle",
        config_schema=[
            {"name": "host", "label": "Host", "type": "string", "required": True},
            {"name": "port", "label": "Port", "type": "number", "default": 1521},
            {"name": "service_name", "label": "Service Name", "type": "string", "required": True},
            {"name": "schema", "label": "Schema (optional)", "type": "string"},
        ],
        secret_schema=[
            {"name": "user", "label": "User", "type": "string", "required": True},
            {"name": "password", "label": "Password", "type": "password", "required": True},
        ],
    )

    def _dsn(self) -> str:
        host = self.config["host"]
        port = self.config.get("port", 1521)
        service = self.config["service_name"]
        return f"{host}:{port}/{service}"

    def _connect(self):
        import oracledb

        return oracledb.connect(
            user=self.secrets["user"],
            password=self.secrets["password"],
            dsn=self._dsn(),
        )

    async def test(self) -> TestResult:
        def _do() -> TestResult:
            try:
                with self._connect() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1 FROM dual")
                    cur.fetchone()
                return TestResult(ok=True, message="Connected to Oracle")
            except Exception as exc:  # noqa: BLE001
                return TestResult(ok=False, message=f"{type(exc).__name__}: {exc}")

        return await asyncio.to_thread(_do)

    async def list_objects(self) -> list[ObjectSpec]:
        def _do() -> list[ObjectSpec]:
            schema = self.config.get("schema") or self.secrets["user"].upper()
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT table_name FROM all_tables WHERE owner = :s ORDER BY table_name",
                    {"s": schema.upper()},
                )
                return [ObjectSpec(name=r[0], label=r[0]) for r in cur.fetchall()]

        try:
            return await asyncio.to_thread(_do)
        except Exception:
            return []

    async def read(
        self, object_name: str, *, batch_size: int = 1000, since: str | None = None
    ) -> AsyncIterator[list[dict[str, Any]]]:
        schema = self.config.get("schema") or self.secrets["user"].upper()
        qualified = f'"{schema.upper()}"."{object_name}"'
        where = ""
        binds: dict[str, Any] = {}
        if since:
            where = " WHERE LAST_MODIFIED > :since"
            binds["since"] = since

        def _fetch_all() -> list[tuple[list[str], list[tuple]]]:
            with self._connect() as conn:
                cur = conn.cursor()
                cur.arraysize = batch_size
                cur.execute(f"SELECT * FROM {qualified}{where}", binds)
                cols = [d[0] for d in cur.description]
                batches: list[tuple[list[str], list[tuple]]] = []
                while True:
                    rows = cur.fetchmany(batch_size)
                    if not rows:
                        break
                    batches.append((cols, rows))
                return batches

        batches = await asyncio.to_thread(_fetch_all)
        for cols, rows in batches:
            yield [dict(zip(cols, r, strict=False)) for r in rows]
