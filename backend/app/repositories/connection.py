from __future__ import annotations

import uuid
from typing import Any

from app.db.surreal import SurrealStore
from app.models import Connection
from app.repositories._common import coerce_datetime, normalise_id, now


class ConnectionRepository:
    table = "connection"

    def __init__(self, store: SurrealStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def list(self, *, role: str | None = None) -> list[Connection]:
        if role:
            rows = await self._store.select_all(
                self.table,
                where="role = $role",
                params={"role": role},
                order_by="created_at DESC",
            )
        else:
            rows = await self._store.select_all(
                self.table, order_by="created_at DESC"
            )
        return [self._to_model(r) for r in rows]

    async def get(self, conn_id: str) -> Connection | None:
        row = await self._store.select_one(self.table, conn_id)
        return self._to_model(row) if row else None

    async def get_by_name(self, name: str) -> Connection | None:
        rows = await self._store.select_all(
            self.table, where="name = $name", params={"name": name}, limit=1
        )
        return self._to_model(rows[0]) if rows else None

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        name: str,
        description: str | None,
        connector_type: str,
        role: str,
        config: dict[str, Any],
        secrets: dict[str, Any],
        status: str = "untested",
    ) -> Connection:
        ts = now()
        record_id = str(uuid.uuid4())
        data = {
            "name": name,
            "description": description,
            "connector_type": connector_type,
            "role": role,
            "config": config,
            "secrets": secrets,
            "status": status,
            "last_tested_at": None,
            "created_at": ts.isoformat(),
            "updated_at": ts.isoformat(),
        }
        row = await self._store.create(self.table, record_id, data)
        return self._to_model(row)

    async def update(self, conn_id: str, patch: dict[str, Any]) -> Connection | None:
        if not patch:
            return await self.get(conn_id)
        data = dict(patch)
        data["updated_at"] = now().isoformat()
        # Datetimes need stringifying before they cross the wire
        if "last_tested_at" in data and data["last_tested_at"] is not None:
            tv = data["last_tested_at"]
            if hasattr(tv, "isoformat"):
                data["last_tested_at"] = tv.isoformat()
        row = await self._store.update(self.table, conn_id, data)
        return self._to_model(row) if row else None

    async def delete(self, conn_id: str) -> bool:
        return await self._store.delete(self.table, conn_id)

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _to_model(row: dict[str, Any]) -> Connection:
        return Connection(
            id=normalise_id(row.get("id")),
            name=row["name"],
            description=row.get("description"),
            connector_type=row["connector_type"],
            role=row["role"],
            config=row.get("config") or {},
            secrets=row.get("secrets") or {},
            status=row.get("status") or "unknown",
            last_tested_at=coerce_datetime(row.get("last_tested_at")),
            created_at=coerce_datetime(row.get("created_at")) or now(),
            updated_at=coerce_datetime(row.get("updated_at")) or now(),
        )
