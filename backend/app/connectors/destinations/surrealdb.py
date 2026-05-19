from __future__ import annotations

from typing import Any

from app.connectors.base import (
    ConnectorMetadata,
    DestinationConnector,
    ObjectSpec,
    TestResult,
)
from app.connectors.registry import registry


@registry.register
class SurrealDbDestination(DestinationConnector):
    metadata = ConnectorMetadata(
        type="surrealdb",
        label="SurrealDB",
        role="destination",
        description="Writes records to a SurrealDB namespace/database",
        icon="surreal",
        config_schema=[
            {"name": "url", "label": "URL", "type": "string", "required": True,
             "placeholder": "ws://localhost:8000/rpc"},
            {"name": "namespace", "label": "Namespace", "type": "string", "required": True},
            {"name": "database", "label": "Database", "type": "string", "required": True},
        ],
        secret_schema=[
            {"name": "username", "label": "Username", "type": "string"},
            {"name": "password", "label": "Password", "type": "password"},
        ],
    )

    async def _client(self):
        from surrealdb import Surreal

        db = Surreal(self.config["url"])
        await db.connect()
        user = self.secrets.get("username")
        pwd = self.secrets.get("password")
        if user and pwd:
            await db.signin({"user": user, "pass": pwd})
        await db.use(self.config["namespace"], self.config["database"])
        return db

    async def test(self) -> TestResult:
        try:
            db = await self._client()
            await db.query("INFO FOR DB")
            await db.close()
            return TestResult(ok=True, message="Connected to SurrealDB")
        except Exception as exc:  # noqa: BLE001
            return TestResult(ok=False, message=f"{type(exc).__name__}: {exc}")

    async def list_objects(self) -> list[ObjectSpec]:
        try:
            db = await self._client()
            info = await db.query("INFO FOR DB")
            await db.close()
            tables = []
            if info and isinstance(info, list):
                result = info[0].get("result", {}) if isinstance(info[0], dict) else {}
                tables = list((result.get("tables") or {}).keys())
            return [ObjectSpec(name=t, label=t) for t in tables]
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
        db = await self._client()
        try:
            written = 0
            for rec in records:
                if mode == "upsert" and "id" in rec:
                    rid = rec.pop("id")
                    await db.update(f"{object_name}:{rid}", rec)
                else:
                    await db.create(object_name, rec)
                written += 1
            return written
        finally:
            await db.close()
