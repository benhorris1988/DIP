from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldSpec:
    name: str
    type: str  # "string" | "int" | "float" | "bool" | "datetime" | "json"
    nullable: bool = True
    primary_key: bool = False


@dataclass
class ObjectSpec:
    """Describes a table / entity set available from a source or destination."""
    name: str
    label: str
    fields: list[FieldSpec] = field(default_factory=list)


@dataclass
class ConnectorMetadata:
    type: str
    label: str
    role: str  # "source" | "destination"
    description: str
    icon: str  # short identifier the UI maps to an icon
    config_schema: list[dict[str, Any]]
    secret_schema: list[dict[str, Any]]


@dataclass
class TestResult:
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    metadata: ConnectorMetadata

    def __init__(self, config: dict[str, Any], secrets: dict[str, Any]):
        self.config = config
        self.secrets = secrets

    @abstractmethod
    async def test(self) -> TestResult: ...

    @abstractmethod
    async def list_objects(self) -> list[ObjectSpec]: ...


class SourceConnector(BaseConnector):
    @abstractmethod
    async def read(
        self, object_name: str, *, batch_size: int = 1000, since: str | None = None
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Yields batches of records from the named source object."""
        if False:
            yield []  # pragma: no cover


class DestinationConnector(BaseConnector):
    @abstractmethod
    async def write(
        self,
        object_name: str,
        records: list[dict[str, Any]],
        *,
        mode: str = "upsert",
    ) -> int:
        """Writes records to the destination object. Returns rows written."""
