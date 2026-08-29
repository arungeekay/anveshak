"""ANVESHAK FastAPI application entrypoint (Catalyst AppSail)."""
from __future__ import annotations

import logging

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

log = logging.getLogger("anveshak.main")

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


@app.get("/")
def root() -> dict:
    """Root route — Catalyst's readiness probe hits '/', so it must return 200."""
    return {"service": "anveshak-api", "status": "ok", "docs": "/api/health"}


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


@app.get("/api/warm")
def warm() -> dict:
    """Keep-alive + cache-warm probe (FINALE_PLAN F-01).

    AppSail idles the container out after inactivity, and a cold start costs 60-90s
    of prewarming — unacceptable in front of a jury. A Catalyst Cron hits this every
    few minutes so the container (and every heavy cache) stays hot.

    Also useful right after a deploy: call it until `cold` is false. Each stage is
    individually guarded so one failure cannot break the keep-alive itself.
    """
    import time as _t

    from .db import get_connection

    timings: dict[str, float] = {}
    cold = False

    def stage(name: str, fn):
        nonlocal cold
        t0 = _t.perf_counter()
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - a warm probe must never 500
            timings[name] = -1.0
            log.warning("warm stage %s failed: %s", name, exc)
            return
        dt = _t.perf_counter() - t0
        timings[name] = round(dt, 3)
        if dt > 2.0:  # anything slow means that cache had to be (re)built
            cold = True

    con = get_connection()
    stage("db", lambda: con.execute("SELECT 1").fetchone())

    from .embeddings import matrix
    stage("embeddings", lambda: matrix.ensure(con))

    from .linkage.store import store as series_store
    stage("series", lambda: series_store.ensure(con))

    from .graph import engine as graph_engine
    stage("graph", lambda: graph_engine.cache.ensure(con))

    from .patrol.store import leads_store
    stage("leads", lambda: leads_store.ensure(con))

    # The demo series' pack is prewarmed at boot; rebuild it here if a restart or a
    # failed prewarm left it missing, so "Open pack" is never cold on stage.
    from .api.investigate import _build_pack, _packs
    stage("pack", lambda: _packs.get("SH-07") or _build_pack(con, "SH-07"))

    return {
        "status": "warm" if not cold else "warming",
        "cold": cold,
        "timings_s": timings,
        "caches": {
            "embeddings": matrix.size(),
            "series": len(series_store.all(con)),
            "graph_nodes": graph_engine.cache.g.number_of_nodes() if graph_engine.cache.g else 0,
            "leads": len(leads_store.all()),
            "packs": sorted(_packs.keys()),
        },
    }


@app.post("/internal/mirror/rebuild")
def mirror_rebuild() -> dict:
    """Re-open the DuckDB analytical mirror (ADR-1). In production this is where the
    Data Store -> DuckDB refresh runs; here it re-attaches the connection so a fresh
    build/anveshak.duckdb is picked up without a restart."""
    from .db import reset_connection

    reset_connection()
    return {"status": "rebuilt", **db_status()}


# --- Frontend (SPA) served from the AppSail origin ------------------------------
# Catalyst Web Client Hosting sits behind an API Gateway that intercepts every .html
# request on the *.catalystserverless.in domain, so the SPA cannot be served there
# while the gateway is enabled. The AppSail domain (*.catalystappsail.in) is raw
# FastAPI with no such interception, so we additionally serve the built bundle here
# at /ui. The bundle calls the API same-origin (relative /api/*), so no CORS hop.
# Guarded: if the dist folder isn't bundled, the API still runs unaffected.
import os as _os  # noqa: E402

from fastapi.staticfiles import StaticFiles  # noqa: E402

_UI_DIR = _os.getenv("UI_DIR", "frontend/dist")
if _os.path.isdir(_UI_DIR):
    app.mount("/ui", StaticFiles(directory=_UI_DIR, html=True), name="ui")
