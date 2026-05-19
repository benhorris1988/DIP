from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.db.surreal import SurrealStore, get_store
from app.services.definitions import load_definitions

router = APIRouter(prefix="/definitions", tags=["definitions"])


@router.post("/reload")
async def reload(store: SurrealStore = Depends(get_store)) -> dict:
    report = await load_definitions(store)
    return report.to_dict()


@router.get("/status")
async def status() -> dict:
    settings = get_settings()
    root = Path(settings.definitions_dir).resolve()
    return {
        "directory": str(root),
        "exists": root.exists(),
        "files": sorted(str(p.relative_to(root)) for p in root.rglob("*.y*ml"))
        if root.exists()
        else [],
    }
