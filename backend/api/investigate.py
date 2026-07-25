"""Investigation Cell endpoints (contracts.md §4): POST /api/investigate + SSE stream."""
from __future__ import annotations

import itertools
import json

import anyio
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..agents.pipeline import investigate
from ..db import get_connection
from ..pdf.pack_render import render_pack_html

router = APIRouter()

_counter = itertools.count(1)
_runs: dict[str, str] = {}     # run_id -> series_id
_packs: dict[str, dict] = {}   # series_id -> pack


class InvestigateRequest(BaseModel):
    series_id: str | None = None
    case_id: int | None = None


@router.post("/api/investigate")
def start(req: InvestigateRequest) -> dict:
    if not req.series_id:
        raise HTTPException(status_code=400, detail="series_id is required")
    run_id = f"r-{next(_counter)}"
    _runs[run_id] = req.series_id
    return {"run_id": run_id, "stream": f"/api/investigate/{run_id}/stream"}


@router.get("/api/investigate/{run_id}/stream")
async def stream(run_id: str):
    series_id = _runs.get(run_id)
    if not series_id:
        raise HTTPException(status_code=404, detail="unknown run_id")
    con = get_connection()

    async def gen():
        # investigate() is a synchronous generator that runs heavy CPU work (SARIMA,
        # HDBSCAN, betweenness) between yields. Stepping it inline would block the
        # event loop and stall health checks / other tabs for the whole run, so we
        # advance it one step at a time in a worker thread. Steps are awaited
        # sequentially, so the shared DuckDB cursor is never touched concurrently.
        it = investigate(con, series_id)
        _END = object()

        def _step():
            try:
                return next(it)
            except StopIteration:
                return _END

        while True:
            item = await anyio.to_thread.run_sync(_step)
            if item is _END:
                break
            event, data = item
            if event == "pack_ready" and data.get("pack"):
                _packs[series_id] = data["pack"]
            yield {"event": event, "data": json.dumps(data)}

    return EventSourceResponse(gen())


def _build_pack(con, series_id: str) -> dict | None:
    for event, data in investigate(con, series_id):
        if event == "pack_ready":
            if data.get("pack"):
                _packs[series_id] = data["pack"]
            return data.get("pack")
    return None


@router.get("/api/investigate/pack/{series_id}.html", response_class=HTMLResponse)
def pack_html(series_id: str) -> str:
    pack = _packs.get(series_id) or _build_pack(get_connection(), series_id)
    return render_pack_html(pack)
