"""Compatibility shim — the metadata store is now SurrealDB.

Historically this module exposed a SQLAlchemy ``AsyncSession`` factory.
The platform's metadata store is SurrealDB now, so the only thing left
here is the FastAPI dependency that yields the process-wide
:class:`SurrealStore` and the lifespan helpers.
"""

from __future__ import annotations

from app.db.surreal import SurrealStore, get_store, store

__all__ = ["SurrealStore", "get_store", "store"]
