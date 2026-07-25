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


@app.get("/internal/llm/diag")
def llm_diag() -> dict:
    """TEMP diagnostic: surface exactly why the QuickML/GLM SDK call fails in AppSail."""
    import traceback

    out: dict = {"model": settings.quickml_model, "endpoint": settings.quickml_endpoint}
    try:
        import zcatalyst_sdk
        from zcatalyst_sdk._http_client import AuthorizedHttpClient
        from zcatalyst_sdk.quick_ml import CatalystService, CredentialUser

        zapp = zcatalyst_sdk.initialize()
        out["initialize"] = "ok"
        client = AuthorizedHttpClient(zapp)
        payload = {"model": settings.quickml_model,
                   "messages": [{"role": "user", "content": "Reply with: OK"}],
                   "max_tokens": 10, "temperature": 0, "stream": False,
                   "chat_template_kwargs": {"enable_thinking": False}}
        resp = client.request(
            method="POST", url=settings.quickml_endpoint, user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.QUICK_ML, external=True, json=payload,
            headers={"Content-Type": "application/json", "CATALYST-ORG": settings.quickml_org})
        out["ok"] = True
        out["response"] = str(resp.response_json)[:600]
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
        out["trace"] = traceback.format_exc()[-1800:]
    return out


@app.post("/internal/mirror/rebuild")
def mirror_rebuild() -> dict:
    """Re-open the DuckDB analytical mirror (ADR-1). In production this is where the
    Data Store -> DuckDB refresh runs; here it re-attaches the connection so a fresh
    build/anveshak.duckdb is picked up without a restart."""
    from .db import reset_connection

    reset_connection()
    return {"status": "rebuilt", **db_status()}
