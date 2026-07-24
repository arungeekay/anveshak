"""POST /api/chat — NL->SQL run_sql path (contracts.md §2). Other tools wired later."""
from __future__ import annotations

import logging

from fastapi import APIRouter

from ..audit import write_audit
from ..db import db_status, get_connection
from ..models import ChatRequest
from ..nl2sql import engine
from .render import build_render_specs, compose_answer, extract_case_ids

log = logging.getLogger("anveshak.chat")
router = APIRouter()


@router.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    if db_status()["db"] != "loaded":
        return {"error": "The crime database is not loaded on this server.",
                "suggestion": "Build the DuckDB mirror (data_engine) or restart the app."}
    con = get_connection()
    try:
        nl = engine.run(con, req.message)
    except engine.EngineError as exc:
        log.info("nl2sql failed for %r: %s", req.message, exc)
        return {"error": "I couldn't translate that into a database query.",
                "suggestion": "Try naming a crime type, a district, and a year "
                              "(e.g. 'chain snatching in Bengaluru City in 2026')."}

    render_specs = build_render_specs(nl.columns, nl.rows, req.message)
    answer_text = compose_answer(req.message, nl.columns, nl.rows, req.lang)
    case_ids = extract_case_ids(nl.columns, nl.rows)
    audit_id = write_audit(con, user_id="demo", role="SCRB", action="chat",
                           detail={"question": req.message, "sql": nl.sql,
                                   "rows": nl.row_count})
    confidence = ("high" if nl.row_count > 0 and not nl.repaired
                  else "low" if nl.row_count == 0 else "medium")
    return {
        "answer_text": answer_text,
        "render_specs": render_specs,
        "evidence": {"tool": "run_sql", "sql": nl.sql, "row_count": nl.row_count,
                     "case_ids": case_ids, "params": {}},
        "followup_context": req.message,
        "confidence": confidence,
        "audit_id": audit_id,
    }
