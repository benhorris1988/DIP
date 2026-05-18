from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Asset, AssetMaterialization, DagRun, Job, Pipeline
from app.schemas.asset import (
    AssetGraph,
    AssetMaterializationOut,
    AssetWithStatus,
    DagRunOut,
    MaterializeRequest,
)
from app.services import graph
from app.services.dag_runner import materialize_assets

router = APIRouter(prefix="/assets", tags=["assets"])


async def _with_status(
    db: AsyncSession, assets: list[Asset]
) -> list[AssetWithStatus]:
    if not assets:
        return []
    keys = [a.key for a in assets]
    pipeline_ids = list({a.pipeline_id for a in assets})

    pipelines = (
        await db.execute(select(Pipeline).where(Pipeline.id.in_(pipeline_ids)))
    ).scalars().all()
    pname = {p.id: p.name for p in pipelines}

    # Most recent materialization per asset
    last_mats: dict[str, AssetMaterialization] = {}
    rows = (
        await db.execute(
            select(AssetMaterialization)
            .where(AssetMaterialization.asset_key.in_(keys))
            .order_by(desc(AssetMaterialization.ts))
        )
    ).scalars().all()
    for row in rows:
        if row.asset_key not in last_mats:
            last_mats[row.asset_key] = row

    # Status comes from the job referenced by the materialization
    job_ids = list({m.job_id for m in last_mats.values()})
    jobs = (
        await db.execute(select(Job).where(Job.id.in_(job_ids)))
    ).scalars().all()
    job_by_id = {j.id: j for j in jobs}

    out: list[AssetWithStatus] = []
    for a in assets:
        mat = last_mats.get(a.key)
        job = job_by_id.get(mat.job_id) if mat else None
        out.append(
            AssetWithStatus(
                id=a.id,
                key=a.key,
                description=a.description,
                pipeline_id=a.pipeline_id,
                connection_id=a.connection_id,
                object_name=a.object_name,
                depends_on=list(a.depends_on or []),
                asset_metadata=dict(a.asset_metadata or {}),
                definition_path=a.definition_path,
                created_at=a.created_at,
                updated_at=a.updated_at,
                pipeline_name=pname.get(a.pipeline_id),
                last_materialized_at=mat.ts if mat else None,
                last_job_id=mat.job_id if mat else None,
                last_status=job.status if job else None,
                rows_written=mat.rows_written if mat else None,
            )
        )
    return out


@router.get("", response_model=list[AssetWithStatus])
async def list_assets(db: AsyncSession = Depends(get_db)) -> list[AssetWithStatus]:
    assets = (await db.execute(select(Asset).order_by(Asset.key))).scalars().all()
    return await _with_status(db, list(assets))


@router.get("/graph", response_model=AssetGraph)
async def asset_graph(db: AsyncSession = Depends(get_db)) -> AssetGraph:
    layers = await graph.layer_assets(db)
    assets = (await db.execute(select(Asset).order_by(Asset.key))).scalars().all()
    nodes = await _with_status(db, list(assets))
    return AssetGraph(layers=layers, nodes=nodes)


@router.get("/{key}", response_model=AssetWithStatus)
async def get_asset(key: str, db: AsyncSession = Depends(get_db)) -> AssetWithStatus:
    asset = (
        await db.execute(select(Asset).where(Asset.key == key))
    ).scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")
    result = await _with_status(db, [asset])
    return result[0]


@router.get("/{key}/materializations", response_model=list[AssetMaterializationOut])
async def list_materializations(
    key: str, limit: int = 50, db: AsyncSession = Depends(get_db)
) -> list[AssetMaterialization]:
    rows = (
        await db.execute(
            select(AssetMaterialization)
            .where(AssetMaterialization.asset_key == key)
            .order_by(desc(AssetMaterialization.ts))
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)


@router.post("/materialize", response_model=DagRunOut)
async def materialize(
    body: MaterializeRequest, db: AsyncSession = Depends(get_db)
) -> DagRun:
    if not body.keys:
        raise HTTPException(422, "keys is required")
    run = await materialize_assets(
        db, body.keys, include_upstream=body.include_upstream
    )
    return run
