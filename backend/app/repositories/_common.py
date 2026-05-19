from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.surreal import strip_table


def now() -> datetime:
    """Single source for "now" — easier to monkey-patch in tests."""
    return datetime.utcnow()


def coerce_datetime(value: Any) -> datetime | None:
    """SurrealDB returns datetimes as ISO strings; coerce to ``datetime``.

    Returns ``None`` for missing / falsy values.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        s = value
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None


def normalise_id(value: Any) -> str:
    """Convert a Surreal record-id-ish value back to a bare id string."""
    if value is None:
        return ""
    return strip_table(value) or ""
