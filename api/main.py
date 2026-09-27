import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jobs.worker import RunWorker
from .routers import auth, sites, runs, artifacts, opportunities, templates, blueprints, gsc


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = None
    if os.environ.get("ENABLE_WORKER", "true").lower() in ("true", "1", "yes"):
        worker = RunWorker()
        worker.start_background()
    yield
    if worker:
        worker.stop()


app = FastAPI(
    title="SEOJEV Platform API",
    version="2.0.0",
    description="FastAPI Backend for SEOJEV Search Intelligence Platform",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "version": "2.0.0"}
