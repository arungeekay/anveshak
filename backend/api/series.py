"""Series (linkage) endpoints (contracts.md §3)."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import get_connection
from ..linkage.store import store

router = APIRouter()


class FeedbackRequest(BaseModel):
    verdict: str  # confirm | reject
    note: str = ""


@router.get("/api/series")
def list_series(limit: int = 50) -> list[dict]:
    return store.all(get_connection())[:limit]


@router.get("/api/series/{series_id}")
def get_series(series_id: str) -> dict:
    h = store.get(get_connection(), series_id)
    if not h:
        raise HTTPException(status_code=404, detail=f"unknown series {series_id}")
    return h


@router.get("/api/series/{series_id}/counterfactual")
def counterfactual(series_id: str) -> dict:
    """When would ANVESHAK have caught this series, and what followed? (F-11)

    Precomputed offline by `python -m eval.counterfactual` — it replays the real
    linkage engine over the corpus truncated at each of the series' case dates,
    which is far too heavy to run per request. The artefact carries its own method
    statement so the claim is auditable rather than asserted.
    """
    path = Path("backend/static_data") / f"counterfactual_{series_id}.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"no counterfactual analysis has been computed for {series_id}")
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/api/series/rescan")
def rescan() -> dict:
    series = store.rescan(get_connection())
    return {"count": len(series), "series_ids": [s["series_id"] for s in series]}


@router.post("/api/series/{series_id}/feedback")
def feedback(series_id: str, body: FeedbackRequest) -> dict:
    h = store.feedback(get_connection(), series_id, body.verdict, body.note)
    if not h:
        raise HTTPException(status_code=404, detail=f"unknown series {series_id}")
    return {"series_id": series_id, "status": h["status"]}
