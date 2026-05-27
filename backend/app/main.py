import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes import (
    assets,
    connections,
    connectors,
    dag_runs,
    definitions,
    jobs,
    pipelines,
    transforms,
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
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(connectors.router, prefix="/api")
app.include_router(connections.router, prefix="/api")
app.include_router(pipelines.router, prefix="/api")
app.include_router(transforms.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(dag_runs.router, prefix="/api")
app.include_router(definitions.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}


# Serve the built Flutter web app from the same origin when present.
# Set DIP_WEB_DIR to override; default looks for ../flutter_app/build/web
# relative to the backend working directory.
_web_dir = Path(
    os.environ.get("DIP_WEB_DIR", "../flutter_app/build/web")
).resolve()
if _web_dir.exists() and (_web_dir / "index.html").exists():

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        # Critical: never serve the SPA shell for API paths. Without this
        # guard a typo like /api/jobsstats would fall through to index.html
        # and the Dio client would TypeError trying to parse HTML as JSON.
        # An honest JSON 404 is the right answer.
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(404, f"No API route at /{full_path}")
        # Serve any file present in the build, falling back to the SPA shell
        # so Flutter's client-side router can take over for unknown paths.
        # The /assets prefix is shared between Flutter's static asset
        # directory *and* its in-app routes, so we resolve real files first
        # and only then fall back to index.html.
        candidate = (_web_dir / full_path).resolve()
        # Guard against ../ traversal escaping the web root
        if (
            full_path
            and candidate.is_file()
            and _web_dir in candidate.parents
        ):
            return FileResponse(candidate)
        return FileResponse(_web_dir / "index.html")

    logger.info("Serving Flutter web app from %s", _web_dir)
else:
    logger.info("No Flutter web build found at %s (set DIP_WEB_DIR to override)", _web_dir)
