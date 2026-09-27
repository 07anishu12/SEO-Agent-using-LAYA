"""
FastAPI Main Application Entrypoint for SEOJEV Platform.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, sites, runs

app = FastAPI(
    title="SEOJEV Platform API",
    version="2.0.0",
    description="FastAPI Backend for SEOJEV Search Intelligence Platform"
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


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "version": "2.0.0"}
