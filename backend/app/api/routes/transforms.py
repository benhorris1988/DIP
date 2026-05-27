from fastapi import APIRouter

from app.services.transforms import catalog_as_dicts

router = APIRouter(prefix="/transforms", tags=["transforms"])


@router.get("")
async def list_transforms() -> list[dict]:
    """Catalog of available transformation step types. Drives the pipeline
    transformation builder UI (labels, config fields, code examples)."""
    return catalog_as_dicts()
