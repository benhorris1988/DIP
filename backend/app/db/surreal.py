"""SurrealDB metadata store.

The platform's own state — connections, pipelines, jobs, assets, dag
runs — lives in SurrealDB, not in a relational store. This module owns
a single long-lived connection (the SurrealDB Python SDK multiplexes
RPC calls over one WebSocket) and exposes a thin, async API:

* :func:`store` returns the process-wide :class:`SurrealStore`.
* :meth:`SurrealStore.query` runs a single SurrealQL statement and
  returns the rows of its first result set.
* :meth:`SurrealStore.create` / ``select`` / ``update`` / ``delete``
  wrap record-level operations on ``table:id`` thing-ids.

Tables and unique indexes are created idempotently on first connect
(``DEFINE TABLE IF NOT EXISTS …``), so no migration tooling is needed.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


# The set of unique indexes that protect business invariants (e.g.
# pipeline names must be unique). All other fields are schemaless.
_SCHEMA = [
    "DEFINE TABLE IF NOT EXISTS connection SCHEMALESS;",
    "DEFINE INDEX IF NOT EXISTS connection_name ON connection FIELDS name UNIQUE;",
    "DEFINE TABLE IF NOT EXISTS pipeline SCHEMALESS;",
    "DEFINE INDEX IF NOT EXISTS pipeline_name ON pipeline FIELDS name UNIQUE;",
    "DEFINE TABLE IF NOT EXISTS job SCHEMALESS;",
    "DEFINE TABLE IF NOT EXISTS asset SCHEMALESS;",
    "DEFINE INDEX IF NOT EXISTS asset_key ON asset FIELDS key UNIQUE;",
    "DEFINE TABLE IF NOT EXISTS asset_materialization SCHEMALESS;",
    "DEFINE TABLE IF NOT EXISTS dag_run SCHEMALESS;",
]


def thing(table: str, id_: str) -> str:
    """Render a SurrealDB record id for use as ``$rid`` in a query.

    Backticks survive UUID dashes; we never inline ids into SQL.
    """
    return f"{table}:`{id_}`"


def strip_table(thing_id: Any) -> Any:
    """Inverse of :func:`thing` for results coming back from Surreal.

    The SDK may return record ids as plain strings (``"pipeline:abc"``)
    or as ``RecordID`` objects depending on version. We normalise to the
    bare id so the API contract (uuid-style ``id`` field) doesn't leak
    SurrealDB syntax to clients.
    """
    if thing_id is None:
        return None
    s = str(thing_id)
    if ":" in s:
        s = s.split(":", 1)[1]
    return s.strip("`⟨⟩")


class SurrealStore:
    """Process-wide async client for the SurrealDB metadata store."""

    def __init__(
        self,
        url: str,
        user: str,
        password: str,
        namespace: str,
        database: str,
    ) -> None:
        self._url = url
        self._user = user
        self._password = password
        self._namespace = namespace
        self._database = database
        self._client: Any = None
        self._connect_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Open the WebSocket, sign in, select ns/db, and define schema.

        Safe to call multiple times. Subsequent calls are a no-op if the
        client is already connected.
        """
        if self._client is not None:
            return
        async with self._connect_lock:
            if self._client is not None:
                return
            from surrealdb import AsyncSurrealDB

            # The 0.4.x SDK appends "/rpc" itself; strip a trailing copy
            # so either configured form (with or without /rpc) works.
            url = self._url
            if url.endswith("/rpc"):
                url = url[: -len("/rpc")]
            client = AsyncSurrealDB(url)
            await client.connect()
            await client.sign_in(self._user, self._password)
            await client.use(self._namespace, self._database)
            for stmt in _SCHEMA:
                await client.query(stmt)
            self._client = client
            logger.info(
                "SurrealDB connected at %s (ns=%s db=%s)",
                self._url,
                self._namespace,
                self._database,
            )

    async def disconnect(self) -> None:
        if self._client is None:
            return
        try:
            await self._client.close()
        except Exception:  # noqa: BLE001
            logger.debug("SurrealDB close raised", exc_info=True)
        finally:
            self._client = None

    # ------------------------------------------------------------------
    # Core ops
    # ------------------------------------------------------------------

    async def query(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Run one SurrealQL statement and return its result rows.

        For ``SELECT`` / ``UPDATE`` / ``CREATE`` / ``DELETE`` the result
        is a list of dicts. Errors raised by the server are surfaced as
        :class:`SurrealError`.
        """
        await self.connect()
        raw = await self._client.query(sql, params or {})
        return _first_result(raw)

    async def query_many(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[list[dict[str, Any]]]:
        """Run a multi-statement script; return one result list per statement."""
        await self.connect()
        raw = await self._client.query(sql, params or {})
        return _all_results(raw)

    async def select_one(self, table: str, id_: str) -> dict[str, Any] | None:
        rows = await self.query(
            "SELECT * FROM type::thing($t, $i)",
            {"t": table, "i": id_},
        )
        if not rows:
            return None
        return _normalise_row(rows[0])

    async def select_all(
        self,
        table: str,
        *,
        where: str | None = None,
        params: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {int(limit)}"
        rows = await self.query(sql, params or {})
        return [_normalise_row(r) for r in rows]

    async def create(
        self, table: str, id_: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        rows = await self.query(
            "CREATE type::thing($t, $i) CONTENT $d",
            {"t": table, "i": id_, "d": data},
        )
        if not rows:
            raise SurrealError(f"CREATE {table}:{id_} returned no row")
        return _normalise_row(rows[0])

    async def update(
        self, table: str, id_: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Patch a record (MERGE semantics — unmentioned fields are kept)."""
        rows = await self.query(
            "UPDATE type::thing($t, $i) MERGE $d",
            {"t": table, "i": id_, "d": data},
        )
        if not rows:
            return None
        return _normalise_row(rows[0])

    async def delete(self, table: str, id_: str) -> bool:
        rows = await self.query(
            "DELETE type::thing($t, $i) RETURN BEFORE",
            {"t": table, "i": id_},
        )
        return bool(rows)

    async def count(
        self, table: str, *, where: str | None = None, params: dict[str, Any] | None = None
    ) -> int:
        sql = f"SELECT count() AS c FROM {table}"
        if where:
            sql += f" WHERE {where}"
        sql += " GROUP ALL"
        rows = await self.query(sql, params or {})
        if not rows:
            return 0
        return int(rows[0].get("c") or 0)


class SurrealError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Result normalisation
#
# Different SurrealDB SDK versions wrap query results slightly differently.
# We accept both common shapes and always hand callers a flat ``list[dict]``.
# ---------------------------------------------------------------------------


def _first_result(raw: Any) -> list[dict[str, Any]]:
    results = _all_results(raw)
    return results[0] if results else []


def _all_results(raw: Any) -> list[list[dict[str, Any]]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        # Single value (e.g. a bare dict or QueryResponse)
        return [_unwrap_one(raw)]
    return [_unwrap_one(stmt) for stmt in raw]


def _unwrap_one(stmt: Any) -> list[dict[str, Any]]:
    """Extract the row list from a single statement's response.

    The 0.4.x SDK returns ``surrealdb.data.models.QueryResponse``
    instances with ``.status`` / ``.result``. Older / alternative
    versions return raw dicts. Either is fine; we surface failures as
    :class:`SurrealError` and otherwise hand callers ``list[dict]``.
    """
    if stmt is None:
        return []
    status = getattr(stmt, "status", None)
    result = getattr(stmt, "result", None)
    if status is not None or result is not None:
        if status and status != "OK":
            raise SurrealError(str(result) or "query failed")
        return _as_list(result)
    if isinstance(stmt, dict) and "result" in stmt:
        status = stmt.get("status")
        if status and status != "OK":
            raise SurrealError(str(stmt.get("result")) or "query failed")
        return _as_list(stmt.get("result"))
    return _as_list(stmt)


def _as_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v is not None]
    return [value]


def _normalise_row(row: Any) -> dict[str, Any]:
    """Convert a Surreal record into a flat dict the API can return.

    The record id comes back as ``"table:id"`` (or a SDK-specific
    ``RecordID``); strip the table prefix so callers see just the bare
    id and field names match the previous SQLAlchemy schema.
    """
    if not isinstance(row, dict):
        return {"value": row}
    out = dict(row)
    if "id" in out:
        out["id"] = strip_table(out["id"])
    return out


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------


_store: SurrealStore | None = None


def configure(store: SurrealStore | None) -> None:
    """Tests use this to inject a store backed by a transient SurrealDB."""
    global _store
    _store = store


def store() -> SurrealStore:
    if _store is None:
        from app.config import get_settings

        settings = get_settings()
        configure(
            SurrealStore(
                url=settings.surrealdb_url,
                user=settings.surrealdb_user,
                password=settings.surrealdb_password,
                namespace=settings.surrealdb_namespace,
                database=settings.surrealdb_database,
            )
        )
    assert _store is not None
    return _store


def get_store() -> SurrealStore:
    """FastAPI dependency that yields the process-wide store."""
    return store()
