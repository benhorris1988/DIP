import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal, get_db
from app.models import Connection, Pipeline
from app.schemas.pipeline import PipelineCreate, PipelineOut, PipelineUpdate
from app.services.runner import run_pipeline

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.get("", response_model=list[PipelineOut])
async def list_pipelines(db: AsyncSession = Depends(get_db)) -> list[Pipeline]:
    return list(
        (await db.execute(select(Pipeline).order_by(Pipeline.created_at.desc()))).scalars().all()
    )


@router.post("", response_model=PipelineOut, status_code=201)
async def create_pipeline(
    payload: PipelineCreate, db: AsyncSession = Depends(get_db)
) -> Pipeline:
    for cid, label in (
        (payload.source_connection_id, "source"),
        (payload.destination_connection_id, "destination"),
    ):
        c = (await db.execute(select(Connection).where(Connection.id == cid))).scalar_one_or_none()
        if not c:
            raise HTTPException(400, f"{label} connection {cid} not found")
        if c.role != label:
            raise HTTPException(400, f"Connection {c.name} is not a {label}")

    pipeline = Pipeline(
        id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        source_connection_id=payload.source_connection_id,
        destination_connection_id=payload.destination_connection_id,
        source_object=payload.source_object,
        destination_object=payload.destination_object,
        mode=payload.mode,
        field_mappings=[fm.model_dump() for fm in payload.field_mappings],
        transform=payload.transform,
        schedule=payload.schedule,
        enabled=payload.enabled,
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)
    return pipeline


@router.get("/{pipeline_id}", response_model=PipelineOut)
async def get_pipeline(pipeline_id: str, db: AsyncSession = Depends(get_db)) -> Pipeline:
    obj = (
        await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Pipeline not found")
    return obj


@router.patch("/{pipeline_id}", response_model=PipelineOut)
async def update_pipeline(
    pipeline_id: str, payload: PipelineUpdate, db: AsyncSession = Depends(get_db)
) -> Pipeline:
    obj = (
        await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Pipeline not found")
    data = payload.model_dump(exclude_unset=True)
    if "field_mappings" in data and data["field_mappings"] is not None:
        data["field_mappings"] = [fm for fm in data["field_mappings"]]
    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{pipeline_id}", status_code=204)
async def delete_pipeline(pipeline_id: str, db: AsyncSession = Depends(get_db)) -> None:
    obj = (
        await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Pipeline not found")
    await db.delete(obj)
    await db.commit()


async def _run_in_background(pipeline_id: str) -> None:
    async with SessionLocal() as session:
        await run_pipeline(session, pipeline_id, triggered_by="manual")


@router.post("/{pipeline_id}/run", status_code=202)
async def trigger_run(
    pipeline_id: str, background: BackgroundTasks, db: AsyncSession = Depends(get_db)
) -> dict:
    obj = (
        await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Pipeline not found")
    background.add_task(_run_in_background, pipeline_id)
    return {"status": "queued", "pipeline_id": pipeline_id}
