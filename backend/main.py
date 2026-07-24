"""ANVESHAK FastAPI application entrypoint (Catalyst AppSail)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
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
