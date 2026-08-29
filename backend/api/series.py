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


@router.get("/api/series/{series_id}/replay")
def replay(series_id: str) -> dict:
    """Chronological frames for animating the series across the map (F-15).

    Watching the dots appear in order — and hop district borders — makes the case
    for cross-district linkage far better than a table does: you see the exact
    moment human coordination would have lost the thread.
    """
    con = get_connection()
    h = store.get(con, series_id)
    if not h:
        raise HTTPException(status_code=404, detail=f"unknown series {series_id}")
    ids = ",".join(str(i) for i in h["case_ids"])
    rows = con.execute(f"""
        SELECT CaseMasterID, CrimeRegisteredDate, latitude, longitude,
               district, police_station
        FROM vw_case_360 WHERE CaseMasterID IN ({ids})
        ORDER BY CrimeRegisteredDate
    """).fetchall()
    frames, seen, hops = [], [], 0
    for r in rows:
        district = r[4]
        if seen and district != seen[-1]:
            hops += 1
        if not seen or district != seen[-1]:
            seen.append(district)
        frames.append({
            "case_id": int(r[0]), "date": str(r[1])[:10],
            "lat": float(r[2]) if r[2] is not None else None,
            "lon": float(r[3]) if r[3] is not None else None,
            "district": district, "police_station": r[5],
            "district_change": len(seen) > 1 and district != seen[-2] if len(seen) > 1 else False,
        })
    span_days = (rows[-1][1] - rows[0][1]).days if len(rows) > 1 else 0
    return {"series_id": series_id, "frames": frames,
            "districts": h["districts"], "district_hops": hops,
            "span_days": span_days}


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
