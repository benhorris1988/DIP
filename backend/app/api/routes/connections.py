import uuid
from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import registry
from app.db.session import get_db
from app.models import Connection
from app.schemas.connection import ConnectionCreate, ConnectionOut, ConnectionUpdate

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", response_model=list[ConnectionOut])
async def list_connections(
    role: str | None = None, db: AsyncSession = Depends(get_db)
) -> list[Connection]:
    stmt = select(Connection).order_by(Connection.created_at.desc())
    if role:
        stmt = stmt.where(Connection.role == role)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=ConnectionOut, status_code=201)
async def create_connection(
    payload: ConnectionCreate, db: AsyncSession = Depends(get_db)
) -> Connection:
    try:
        registry.get(payload.connector_type)
    except KeyError as exc:
        raise HTTPException(400, str(exc)) from exc

    conn = Connection(
        id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        connector_type=payload.connector_type,
        role=payload.role,
        config=payload.config,
        secrets=payload.secrets,
        status="untested",
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn


@router.get("/{conn_id}", response_model=ConnectionOut)
async def get_connection(conn_id: str, db: AsyncSession = Depends(get_db)) -> Connection:
    obj = (await db.execute(select(Connection).where(Connection.id == conn_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Connection not found")
    return obj


@router.patch("/{conn_id}", response_model=ConnectionOut)
async def update_connection(
    conn_id: str, payload: ConnectionUpdate, db: AsyncSession = Depends(get_db)
) -> Connection:
    obj = (await db.execute(select(Connection).where(Connection.id == conn_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Connection not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{conn_id}", status_code=204)
async def delete_connection(conn_id: str, db: AsyncSession = Depends(get_db)) -> None:
    obj = (await db.execute(select(Connection).where(Connection.id == conn_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Connection not found")
    await db.delete(obj)
    await db.commit()


@router.post("/{conn_id}/test")
async def test_connection(conn_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    obj = (await db.execute(select(Connection).where(Connection.id == conn_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Connection not found")
    connector = registry.instance(obj.connector_type, obj.config, obj.secrets)
    result = await connector.test()
    obj.status = "healthy" if result.ok else "error"
    obj.last_tested_at = datetime.utcnow()
    await db.commit()
    return {"ok": result.ok, "message": result.message, "details": result.details}


@router.get("/{conn_id}/objects")
async def list_objects(conn_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    obj = (await db.execute(select(Connection).where(Connection.id == conn_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Connection not found")
    connector = registry.instance(obj.connector_type, obj.config, obj.secrets)
    objects = await connector.list_objects()
    return [asdict(o) for o in objects]
