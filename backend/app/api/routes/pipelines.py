from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.db.surreal import SurrealStore, get_store
from app.repositories import ConnectionRepository, PipelineRepository
from app.schemas.pipeline import PipelineCreate, PipelineOut, PipelineUpdate
from app.services.runner import run_pipeline

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


def _repo(store: SurrealStore = Depends(get_store)) -> PipelineRepository:
    return PipelineRepository(store)


@router.get("", response_model=list[PipelineOut])
async def list_pipelines(
    repo: PipelineRepository = Depends(_repo),
) -> list[PipelineOut]:
    items = await repo.list()
    return [PipelineOut.model_validate(i, from_attributes=True) for i in items]


@router.post("", response_model=PipelineOut, status_code=201)
async def create_pipeline(
    payload: PipelineCreate,
    store: SurrealStore = Depends(get_store),
) -> PipelineOut:
    pipelines = PipelineRepository(store)
    connections = ConnectionRepository(store)

    for cid, label in (
        (payload.source_connection_id, "source"),
        (payload.destination_connection_id, "destination"),
    ):
        c = await connections.get(cid)
        if not c:
            raise HTTPException(400, f"{label} connection {cid} not found")
        if c.role != label:
            raise HTTPException(400, f"Connection {c.name} is not a {label}")

    if await pipelines.get_by_name(payload.name):
        raise HTTPException(409, f"A pipeline named {payload.name!r} already exists")

    pipeline = await pipelines.create(
        data={
            "name": payload.name,
            "description": payload.description,
            "source_connection_id": payload.source_connection_id,
            "destination_connection_id": payload.destination_connection_id,
            "source_object": payload.source_object,
            "destination_object": payload.destination_object,
            "mode": payload.mode,
            "field_mappings": [fm.model_dump() for fm in payload.field_mappings],
            "transform": payload.transform,
            "schedule": payload.schedule,
            "enabled": payload.enabled,
            "incremental_field": payload.incremental_field,
            "key_columns": payload.key_columns,
        }
    )
    return PipelineOut.model_validate(pipeline, from_attributes=True)


@router.get("/{pipeline_id}", response_model=PipelineOut)
async def get_pipeline(
    pipeline_id: str, repo: PipelineRepository = Depends(_repo)
) -> PipelineOut:
    obj = await repo.get(pipeline_id)
    if not obj:
        raise HTTPException(404, "Pipeline not found")
    return PipelineOut.model_validate(obj, from_attributes=True)


@router.patch("/{pipeline_id}", response_model=PipelineOut)
async def update_pipeline(
    pipeline_id: str,
    payload: PipelineUpdate,
    repo: PipelineRepository = Depends(_repo),
) -> PipelineOut:
    if not await repo.get(pipeline_id):
        raise HTTPException(404, "Pipeline not found")
    data = payload.model_dump(exclude_unset=True)
    if "field_mappings" in data and data["field_mappings"] is not None:
        data["field_mappings"] = [
            fm if isinstance(fm, dict) else fm.model_dump()
            for fm in data["field_mappings"]
        ]
    obj = await repo.update(pipeline_id, data)
    if obj is None:
        raise HTTPException(404, "Pipeline not found")
    return PipelineOut.model_validate(obj, from_attributes=True)


@router.delete("/{pipeline_id}", status_code=204)
async def delete_pipeline(
    pipeline_id: str, repo: PipelineRepository = Depends(_repo)
) -> None:
    if not await repo.delete(pipeline_id):
        raise HTTPException(404, "Pipeline not found")


async def _run_in_background(pipeline_id: str) -> None:
    from app.db.surreal import store as get_store_fn

    await run_pipeline(get_store_fn(), pipeline_id, triggered_by="manual")


@router.post("/{pipeline_id}/run", status_code=202)
async def trigger_run(
    pipeline_id: str,
    background: BackgroundTasks,
    repo: PipelineRepository = Depends(_repo),
) -> dict:
    obj = await repo.get(pipeline_id)
    if not obj:
        raise HTTPException(404, "Pipeline not found")
    background.add_task(_run_in_background, pipeline_id)
    return {"status": "queued", "pipeline_id": pipeline_id}
