"""ANVESHAK FastAPI application entrypoint (Catalyst AppSail)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api import audit as audit_api
from .api import chat as chat_api
from .api import graph as graph_api
from .api import investigate as investigate_api
from .api import leads as leads_api
from .api import series as series_api
from .config import settings
from .db import db_status

app = FastAPI(
    title="ANVESHAK API",
    version=__version__,
    description="Autonomous AI investigation bureau for the Karnataka State Police.",
)

# Frontend is hosted separately (Catalyst Web Client Hosting); allow it in dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_api.router)
app.include_router(series_api.router)
app.include_router(graph_api.router)
app.include_router(investigate_api.router)
app.include_router(leads_api.router)
app.include_router(audit_api.router)


@app.get("/api/health")
def health() -> dict:
    """Liveness + data-layer status."""
    status = db_status()
    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.environment,
        "llm_backend": settings.llm_backend,
        **status,
    }


@app.post("/internal/mirror/rebuild")
def mirror_rebuild() -> dict:
    """Re-open the DuckDB analytical mirror (ADR-1). In production this is where the
    Data Store -> DuckDB refresh runs; here it re-attaches the connection so a fresh
    build/anveshak.duckdb is picked up without a restart."""
    from .db import reset_connection

    reset_connection()
    return {"status": "rebuilt", **db_status()}
