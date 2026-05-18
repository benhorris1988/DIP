import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    assets,
    connections,
    connectors,
    dag_runs,
    definitions,
    jobs,
    pipelines,
)
from app.config import get_settings
from app.db.session import async_session, init_db
from app.services.definitions import load_definitions
from app.services.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)
settings = get_settings()
logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if settings.autoload_definitions:
        try:
            async with async_session() as db:
                report = await load_definitions(db)
            if report.pipelines_total or report.errors:
                logger.info(
                    "Loaded %d pipelines (%d errors) from %s",
                    report.pipelines_total,
                    report.errors,
                    report.directory,
                )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to autoload pipeline definitions")
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(connectors.router, prefix="/api")
app.include_router(connections.router, prefix="/api")
app.include_router(pipelines.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(dag_runs.router, prefix="/api")
app.include_router(definitions.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}
