from __future__ import annotations

from typing import Any

from app.connectors.base import BaseConnector, ConnectorMetadata


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, type[BaseConnector]] = {}

    def register(self, connector_cls: type[BaseConnector]) -> type[BaseConnector]:
        meta = connector_cls.metadata
        key = meta.type
        if key in self._connectors:
            raise ValueError(f"Connector '{key}' already registered")
        self._connectors[key] = connector_cls
        return connector_cls

    def get(self, connector_type: str) -> type[BaseConnector]:
        if connector_type not in self._connectors:
            raise KeyError(f"Unknown connector type '{connector_type}'")
        return self._connectors[connector_type]

    def instance(
        self, connector_type: str, config: dict[str, Any], secrets: dict[str, Any]
    ) -> BaseConnector:
        return self.get(connector_type)(config, secrets)

    def list_metadata(self, role: str | None = None) -> list[ConnectorMetadata]:
        items = [cls.metadata for cls in self._connectors.values()]
        if role:
            items = [m for m in items if m.role == role]
        return items


registry = ConnectorRegistry()
