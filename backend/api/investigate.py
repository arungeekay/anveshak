"""Investigation Cell endpoints (contracts.md §4): POST /api/investigate + SSE stream."""
from __future__ import annotations

import asyncio
import itertools
import json
import logging
import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..agents.pipeline import investigate
from ..db import get_connection
from ..pdf.pack_render import render_pack_html

router = APIRouter()
log = logging.getLogger("anveshak.investigate")

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

    async def gen():
        # investigate() is a synchronous generator that runs heavy CPU work (SARIMA,
        # HDBSCAN, betweenness) between yields. Run the WHOLE generator in one
        # dedicated worker thread and hand events to the event loop via a thread-safe
        # queue. One thread => the generator opens its own thread-local DuckDB cursor
        # (get_connection is called inside the worker) and never shares a cursor
        # across threads; the event loop stays free the entire run.
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()
        _END = object()

        def worker():
            try:
                con = get_connection()  # cursor bound to THIS worker thread
                for event, data in investigate(con, series_id):
                    if event == "pack_ready" and data.get("pack"):
                        _packs[series_id] = data["pack"]
                    loop.call_soon_threadsafe(q.put_nowait, (event, data))
            except Exception as exc:  # noqa: BLE001 - surface as a stream error, don't hang
                log.warning("investigation stream failed for %s: %s", series_id, exc)
                loop.call_soon_threadsafe(
                    q.put_nowait, ("error", {"detail": "investigation failed"}))
            finally:
                loop.call_soon_threadsafe(q.put_nowait, _END)

        threading.Thread(target=worker, name=f"invest-{series_id}", daemon=True).start()
        while True:
            item = await q.get()
            if item is _END:
                break
            event, data = item
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
