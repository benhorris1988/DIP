from app.connectors.registry import registry

# Import to trigger registration
from app.connectors.sources import oracle, sap_odata  # noqa: F401
from app.connectors.destinations import mssql, surrealdb  # noqa: F401

__all__ = ["registry"]
