"""Investigation Cell endpoints (contracts.md §4): POST /api/investigate + SSE stream."""
from __future__ import annotations

import asyncio
import itertools
import json
import logging
import threading

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..agents.pipeline import investigate
from ..db import get_connection
from ..llm.request_ctx import current_request
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


@router.get("/api/investigate/{series_id}/pack")
def get_pack(series_id: str) -> dict:
    """Return the assembled pack for a series (JSON), matching the SSE pack_ready
    payload. The AppSail gateway can sever a long SSE before pack_ready fires, but the
    stream's worker thread finishes and caches the pack here, so the UI falls back to
    polling this endpoint. Returns pack=None while it's still being assembled."""
    pack = _packs.get(series_id)
    return {
        "pack_id": None,
        "pdf_url": f"/api/investigate/pack/{series_id}.html" if pack else None,
        "pack": pack,
    }


def _build_pack(con, series_id: str) -> dict | None:
    for event, data in investigate(con, series_id):
        if event == "pack_ready":
            if data.get("pack"):
                _packs[series_id] = data["pack"]
            return data.get("pack")
    return None


@router.get("/api/investigate/pack/{series_id}.pdf")
def pack_pdf_route(series_id: str, request: Request):
    """Court-ready PDF of the Investigation Pack, rendered by Catalyst SmartBrowz.

    Falls back to the HTML pack (which carries print CSS) when SmartBrowz is
    unavailable, so the download button is never dead in front of a jury.
    """
    from fastapi.responses import RedirectResponse, Response

    from ..pdf.smartbrowz import SmartBrowzUnavailable, pack_pdf

    current_request.set(request)  # SmartBrowz needs the incoming Catalyst headers
    pack = _packs.get(series_id) or _build_pack(get_connection(), series_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"unknown series {series_id}")
    try:
        data = pack_pdf(series_id, render_pack_html(pack))
    except SmartBrowzUnavailable as exc:
        log.warning("pack pdf unavailable (%s); serving HTML instead", exc)
        return RedirectResponse(url=f"/api/investigate/pack/{series_id}.html",
                                status_code=302)
    return Response(content=data, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="ANVESHAK_pack_{series_id}.pdf"'})


@router.get("/api/investigate/pack/{series_id}.html", response_class=HTMLResponse)
def pack_html(series_id: str) -> str:
    pack = _packs.get(series_id) or _build_pack(get_connection(), series_id)
    return render_pack_html(pack)
