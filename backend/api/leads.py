"""Night Patrol lead feed endpoints (contracts.md §5)."""
from __future__ import annotations

from fastapi import APIRouter

from ..db import get_connection
from ..patrol.store import leads_store

router = APIRouter()


@router.post("/api/leads/run")
def run() -> dict:
    leads = leads_store.run(get_connection())
    return {"count": len(leads), "leads": leads}


@router.get("/api/leads")
def list_leads(limit: int = 50) -> list[dict]:
    # ensure() runs the detectors once (stampede-locked) and caches the result.
    return leads_store.ensure(get_connection())[:limit]
