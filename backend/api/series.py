"""Series (linkage) endpoints (contracts.md §3)."""
from __future__ import annotations

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
