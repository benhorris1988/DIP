import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import connections, connectors, jobs, pipelines
from app.config import get_settings
from app.db.session import init_db

settings = get_settings()
logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


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


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}
