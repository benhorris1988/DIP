from app.connectors.registry import registry

# Import to trigger registration
from app.connectors.sources import mssql as mssql_source  # noqa: F401
from app.connectors.sources import oracle, sap_odata  # noqa: F401
from app.connectors.destinations import (  # noqa: F401
    databricks_sql,
    fabric_warehouse,
    mssql,
    surrealdb,
)

__all__ = ["registry"]
