from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.db.surreal import SurrealStore, get_store
from app.models import Asset
from app.repositories import (
    AssetMaterializationRepository,
    AssetRepository,
    JobRepository,
    PipelineRepository,
)
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
    store: SurrealStore, assets: list[Asset]
) -> list[AssetWithStatus]:
    if not assets:
        return []
    pipelines_repo = PipelineRepository(store)
    mats_repo = AssetMaterializationRepository(store)
    jobs_repo = JobRepository(store)

    all_pipelines = await pipelines_repo.list()
    pname = {p.id: p.name for p in all_pipelines}

    last_mats = await mats_repo.latest_per_asset()

    job_ids = {m.job_id for m in last_mats.values()}
    job_by_id = {}
    for jid in job_ids:
        j = await jobs_repo.get(jid)
        if j:
            job_by_id[j.id] = j

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
                freshness_policy=dict(a.freshness_policy or {}),
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
async def list_assets(
    store: SurrealStore = Depends(get_store),
) -> list[AssetWithStatus]:
    assets = await AssetRepository(store).list()
    return await _with_status(store, assets)


@router.get("/graph", response_model=AssetGraph)
async def asset_graph(store: SurrealStore = Depends(get_store)) -> AssetGraph:
    repo = AssetRepository(store)
    layers = await graph.layer_assets(repo)
    assets = await repo.list()
    nodes = await _with_status(store, assets)
    return AssetGraph(layers=layers, nodes=nodes)


@router.get("/{key}", response_model=AssetWithStatus)
async def get_asset(
    key: str, store: SurrealStore = Depends(get_store)
) -> AssetWithStatus:
    asset = await AssetRepository(store).get_by_key(key)
    if not asset:
        raise HTTPException(404, "Asset not found")
    result = await _with_status(store, [asset])
    return result[0]


@router.get("/{key}/materializations", response_model=list[AssetMaterializationOut])
async def list_materializations(
    key: str, limit: int = 50, store: SurrealStore = Depends(get_store)
) -> list[AssetMaterializationOut]:
    rows = await AssetMaterializationRepository(store).list_for_asset(key, limit=limit)
    return [AssetMaterializationOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/materialize", response_model=DagRunOut)
async def materialize(
    body: MaterializeRequest, store: SurrealStore = Depends(get_store)
) -> DagRunOut:
    if not body.keys:
        raise HTTPException(422, "keys is required")
    run = await materialize_assets(
        store, body.keys, include_upstream=body.include_upstream
    )
    return DagRunOut.model_validate(run, from_attributes=True)
