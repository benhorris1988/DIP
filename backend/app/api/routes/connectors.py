from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from app.connectors import registry

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("")
async def list_connectors(role: str | None = None) -> list[dict]:
    return [asdict(m) for m in registry.list_metadata(role)]


@router.get("/{connector_type}")
async def get_connector(connector_type: str) -> dict:
    try:
        return asdict(registry.get(connector_type).metadata)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
