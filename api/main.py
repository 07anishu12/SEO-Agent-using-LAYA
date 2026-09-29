import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jobs.worker import RunWorker
from jobs.scheduler import get_watch_scheduler
from .routers import auth, sites, runs, artifacts, opportunities, templates, blueprints, gsc, work_orders, diff, watch, alerts, trends, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = None
    scheduler = None
    if os.environ.get("ENABLE_WORKER", "true").lower() in ("true", "1", "yes"):
        worker = RunWorker()
        worker.start_background()
    if os.environ.get("ENABLE_SCHEDULER", "false").lower() in ("true", "1", "yes"):
        scheduler = get_watch_scheduler()
        scheduler.start()
    yield
    if scheduler:
        scheduler.stop()
    if worker:
        worker.stop()


from .security import global_exception_handler

app = FastAPI(
    title="SEOJEV Platform API",
    version="2.0.0",
    description="FastAPI Backend for SEOJEV Search Intelligence Platform",
    lifespan=lifespan
)

app.add_exception_handler(Exception, global_exception_handler)

from .config import CORS_ORIGINS
from database.connection import check_db_health
from jobs.queue import check_redis_health
from services.object_store import check_storage_health
from laya.analyzer import LayaSEOAnalyzer
from fastapi import Response, status

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True if CORS_ORIGINS else False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth.router)
app.include_router(sites.router)
app.include_router(runs.router)
app.include_router(artifacts.router)
app.include_router(opportunities.router)
app.include_router(templates.router)
app.include_router(blueprints.router)
app.include_router(gsc.router)
app.include_router(work_orders.router)
app.include_router(diff.router)
app.include_router(watch.router)
app.include_router(alerts.router)
app.include_router(trends.router)
app.include_router(search.router)


@app.get("/health", tags=["system"])
@app.get("/health/liveness", tags=["system"])
def health_liveness():
    """Liveness probe: confirms API process is running and responsive."""
    return {"status": "ok", "version": "2.0.0"}


@app.get("/health/ready", tags=["system"])
@app.get("/ready", tags=["system"])
def health_readiness(response: Response):
    """
    Readiness probe: validates availability of database, Redis queue,
    object storage, and the local Laya inference runtime.
    """
    db_h = check_db_health()
    redis_h = check_redis_health()
    storage_h = check_storage_health()

    laya_analyzer = LayaSEOAnalyzer.get_singleton()
    laya_h = laya_analyzer.get_health()

    all_healthy = (
        db_h.get("healthy", False)
        and redis_h.get("healthy", False)
        and storage_h.get("healthy", False)
        and laya_h.get("apple_silicon_compatible", True)
    )

    result = {
        "status": "ready" if all_healthy else "degraded",
        "components": {
            "database": db_h,
            "redis": redis_h,
            "object_storage": storage_h,
            "laya": laya_h
        }
    }

    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return result
