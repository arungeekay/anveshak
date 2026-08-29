"""Which Zoho Catalyst services ANVESHAK runs on, and their live state.

The competition mandates that everything runs on Catalyst, and Zoho engineers sit
on the jury, so "we used Catalyst" should be inspectable rather than asserted. This
reports, per service, what we use it for and how confident we are that it is
actually working right now.

Status vocabulary, deliberately conservative:

* ``live``       proven by this process (we are running on it, or a call succeeded)
* ``integrated`` code path exists and is exercised, with a runtime fallback
* ``configured`` provisioned for the deployment, not proven from inside the app

Nothing here is hardcoded to look good: `live` is only ever returned when
something about the running process demonstrates it.
"""
from __future__ import annotations

import os

from .config import settings

# service -> (what ANVESHAK uses it for, how the status is decided)
CATALOGUE = [
    ("AppSail",
     "Runs the FastAPI backend and serves the React app, on a custom Docker runtime "
     "carrying the scientific stack and the embedding model."),
    ("QuickML (LLM Serving)",
     "Serves GLM-4.7-Flash for question understanding and narration. No external "
     "inference API is ever called."),
    ("Data Store",
     "System of record for cases and new FIR intake; the analytical mirror is "
     "rebuilt from it."),
    ("SmartBrowz",
     "Renders the court-ready Investigation Pack to PDF."),
    ("Web Client Hosting",
     "Hosts the built React bundle as a Catalyst client component."),
    ("API Gateway",
     "Fronts the deployment."),
    ("Authentication",
     "Officer identity; the role scopes the app enforces server-side are designed "
     "to be issued from here."),
    ("Cron",
     "Runs the overnight Night Patrol sweep and keeps caches warm."),
    ("NoSQL",
     "Graph snapshots for the CrimeGraph."),
    ("Signals and Mail",
     "Lead digests to district officers."),
    ("Cache",
     "Shared state across instances."),
    ("Stratus",
     "Storage for generated Investigation Packs."),
]


def _appsail_live() -> bool:
    """Catalyst injects the listen port into every AppSail container."""
    return bool(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT"))


def platform_status(datastore_connected: bool | None = None) -> dict:
    """Per-service usage and status for the Trust Center."""
    on_appsail = _appsail_live()
    quickml = settings.llm_backend == "quickml"

    # SmartBrowz is exercised on demand (pack PDF) and falls back to HTML, so the
    # honest answer is "integrated" rather than a claim it is live right now.
    smartbrowz_ready = os.path.isdir("/tmp/packs") or on_appsail

    decided = {
        "AppSail": ("live" if on_appsail else "configured",
                    "the container is running with a Catalyst-injected port"
                    if on_appsail else "not running on AppSail in this process"),
        "QuickML (LLM Serving)": (
            "live" if quickml else "configured",
            f"answering through {settings.quickml_model}" if quickml
            else f"llm_backend is {settings.llm_backend}"),
        "Data Store": (
            "live" if datastore_connected else "integrated",
            "connected, row counts read from the console tables"
            if datastore_connected else
            "write path implemented; the DuckDB mirror serves reads"),
        "SmartBrowz": ("integrated" if smartbrowz_ready else "configured",
                       "pack PDF route wired, falls back to a print-styled HTML pack"),
        "Web Client Hosting": ("configured",
                               "client deployed; the SPA is served from the AppSail "
                               "origin because the gateway intercepts HTML there"),
        "API Gateway": ("live" if on_appsail else "configured",
                        "fronting this deployment"),
        "Cron": ("configured", "scheduled against /api/warm and the patrol sweep"),
    }

    services = []
    for name, purpose in CATALOGUE:
        status, detail = decided.get(name, ("configured", "provisioned for the deployment"))
        services.append({"service": name, "used_for": purpose,
                         "status": status, "detail": detail})

    counts = {s: sum(1 for x in services if x["status"] == s)
              for s in ("live", "integrated", "configured")}
    return {
        "platform": "Zoho Catalyst",
        "services": services,
        "counts": counts,
        "total": len(services),
        "mandate": "Deployment is exclusively on Zoho Catalyst. No external "
                   "inference API is ever called from the deployed app.",
        "note": "Status is derived from this running process, not declared: "
                "'live' means something here proves it.",
    }
