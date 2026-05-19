from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException

from app.connectors import registry
from app.db.surreal import SurrealStore, get_store
from app.repositories import ConnectionRepository
from app.repositories._common import now
from app.schemas.connection import ConnectionCreate, ConnectionOut, ConnectionUpdate

router = APIRouter(prefix="/connections", tags=["connections"])


def _repo(store: SurrealStore = Depends(get_store)) -> ConnectionRepository:
    return ConnectionRepository(store)


@router.get("", response_model=list[ConnectionOut])
async def list_connections(
    role: str | None = None,
    repo: ConnectionRepository = Depends(_repo),
) -> list[ConnectionOut]:
    items = await repo.list(role=role)
    return [ConnectionOut.model_validate(i, from_attributes=True) for i in items]


@router.post("", response_model=ConnectionOut, status_code=201)
async def create_connection(
    payload: ConnectionCreate,
    repo: ConnectionRepository = Depends(_repo),
) -> ConnectionOut:
    try:
        registry.get(payload.connector_type)
    except KeyError as exc:
        raise HTTPException(400, str(exc)) from exc

    # Reject duplicates explicitly so the client sees a clean 409 rather
    # than a SurrealDB unique-index violation surfacing as a 500.
    if await repo.get_by_name(payload.name):
        raise HTTPException(409, f"A connection named {payload.name!r} already exists")

    conn = await repo.create(
        name=payload.name,
        description=payload.description,
        connector_type=payload.connector_type,
        role=payload.role,
        config=payload.config,
        secrets=payload.secrets,
    )
    return ConnectionOut.model_validate(conn, from_attributes=True)


@router.get("/{conn_id}", response_model=ConnectionOut)
async def get_connection(
    conn_id: str, repo: ConnectionRepository = Depends(_repo)
) -> ConnectionOut:
    obj = await repo.get(conn_id)
    if not obj:
        raise HTTPException(404, "Connection not found")
    return ConnectionOut.model_validate(obj, from_attributes=True)


@router.patch("/{conn_id}", response_model=ConnectionOut)
async def update_connection(
    conn_id: str,
    payload: ConnectionUpdate,
    repo: ConnectionRepository = Depends(_repo),
) -> ConnectionOut:
    if not await repo.get(conn_id):
        raise HTTPException(404, "Connection not found")
    patch = payload.model_dump(exclude_unset=True)
    obj = await repo.update(conn_id, patch)
    if obj is None:
        raise HTTPException(404, "Connection not found")
    return ConnectionOut.model_validate(obj, from_attributes=True)


@router.delete("/{conn_id}", status_code=204)
async def delete_connection(
    conn_id: str, repo: ConnectionRepository = Depends(_repo)
) -> None:
    if not await repo.delete(conn_id):
        raise HTTPException(404, "Connection not found")


@router.post("/{conn_id}/test")
async def test_connection(
    conn_id: str, repo: ConnectionRepository = Depends(_repo)
) -> dict:
    obj = await repo.get(conn_id)
    if not obj:
        raise HTTPException(404, "Connection not found")
    connector = registry.instance(obj.connector_type, obj.config, obj.secrets)
    result = await connector.test()
    await repo.update(
        conn_id,
        {
            "status": "healthy" if result.ok else "error",
            "last_tested_at": now().isoformat(),
        },
    )
    return {"ok": result.ok, "message": result.message, "details": result.details}


@router.get("/{conn_id}/objects")
async def list_objects(
    conn_id: str, repo: ConnectionRepository = Depends(_repo)
) -> list[dict]:
    obj = await repo.get(conn_id)
    if not obj:
        raise HTTPException(404, "Connection not found")
    connector = registry.instance(obj.connector_type, obj.config, obj.secrets)
    objects = await connector.list_objects()
    return [asdict(o) for o in objects]
