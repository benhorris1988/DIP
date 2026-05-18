from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.definitions import load_definitions

router = APIRouter(prefix="/definitions", tags=["definitions"])


@router.post("/reload")
async def reload(db: AsyncSession = Depends(get_db)) -> dict:
    report = await load_definitions(db)
    return report.to_dict()


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)) -> dict:
    # Same shape as /reload but without mutating — handy for the UI to show
    # what *would* be loaded.
    from app.config import get_settings
    from pathlib import Path

    settings = get_settings()
    root = Path(settings.definitions_dir).resolve()
    return {
        "directory": str(root),
        "exists": root.exists(),
        "files": sorted(str(p.relative_to(root)) for p in root.rglob("*.y*ml"))
        if root.exists()
        else [],
    }
