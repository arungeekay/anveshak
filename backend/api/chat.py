"""POST /api/chat — routes to a deterministic tool or the NL->SQL run_sql path.

Every number in every answer comes from a tool result (ADR-2). The evidence block
names the tool used so the frontend evidence drawer can show provenance.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from ..audit import write_audit
from ..db import db_status, get_connection
from ..llm.adapter import LLMError
from ..models import ChatRequest
from ..nl2sql import engine
from ..nl2sql.router import route
from ..tools.forecast import forecast
from ..tools.hotspots import hotspots
from ..tools.linkage_scan import linkage_scan
from ..tools.network import network
from ..tools.risk_score import risk_rank
from .render import (
    build_render_specs,
    compose_answer,
    extract_case_ids,
    forecast_spec,
    graph_spec,
    map_spec,
)

log = logging.getLogger("anveshak.chat")
router = APIRouter()


def _resp(answer, specs, tool, *, sql=None, row_count=0, case_ids=None, params=None,
          confidence="high", audit_id=0, follow="") -> dict:
    return {
        "answer_text": answer, "render_specs": specs,
        "evidence": {"tool": tool, "sql": sql, "row_count": row_count,
                     "case_ids": case_ids or [], "params": params or {}},
        "followup_context": follow, "confidence": confidence, "audit_id": audit_id,
    }


def _run_sql_path(con, req: ChatRequest, audit) -> dict:
    try:
        nl = engine.run(con, req.message)
    except LLMError as exc:
        log.warning("LLM unavailable for chat: %s", exc)
        return {"error": "The language model is not reachable right now.",
                "suggestion": "The database, series, graph, and patrol features still work. "
                              "Try again shortly."}
    except engine.EngineError as exc:
        log.info("nl2sql failed for %r: %s", req.message, exc)
        return {"error": "I couldn't translate that into a database query.",
                "suggestion": "Try naming a crime type, a district, and a year."}
    specs = build_render_specs(nl.columns, nl.rows, req.message)
    answer = compose_answer(req.message, nl.columns, nl.rows, req.lang)
    conf = "high" if nl.row_count > 0 and not nl.repaired else "low" if nl.row_count == 0 else "medium"
    aid = audit("chat", {"question": req.message, "sql": nl.sql, "rows": nl.row_count})
    return _resp(answer, specs, "run_sql", sql=nl.sql, row_count=nl.row_count,
                 case_ids=extract_case_ids(nl.columns, nl.rows), confidence=conf,
                 audit_id=aid, follow=req.message)


@router.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    if db_status()["db"] != "loaded":
        return {"error": "The crime database is not loaded on this server.",
                "suggestion": "Build the DuckDB mirror (data_engine) or restart the app."}
    con = get_connection()

    def audit(action, detail):
        return write_audit(con, user_id="demo", role="SCRB", action=action, detail=detail)

    intent, params = route(con, req.message)

    if intent == "linkage":
        series = linkage_scan(con=con)
        top = series[:5]
        cols = ["series_id", "crime_sub_head", "districts", "cases", "confidence"]
        rows = [[s["series_id"], s["crime_sub_head"], ", ".join(s["districts"]),
                 len(s["case_ids"]), s["confidence"]] for s in top]
        specs = [{"type": "table", "title": "Detected series",
                  "table": {"columns": cols, "rows": rows}}]
        answer = (f"Found {len(series)} candidate series. Top: "
                  + "; ".join(f"{s['series_id']} ({s['crime_sub_head']}, {len(s['case_ids'])} cases, "
                              f"conf {s['confidence']})" for s in top[:3]) + ".") if series else \
                 "No linked series detected."
        aid = audit("chat", {"question": req.message, "tool": "linkage_scan", "n": len(series)})
        return _resp(answer, specs, "linkage_scan",
                     case_ids=top[0]["case_ids"] if top else [], audit_id=aid)

    if intent == "network":
        gr = network(person_key=params["person_key"], con=con)
        specs = [graph_spec(gr, title="Network")]
        aid = audit("chat", {"question": req.message, "tool": "network",
                             "person": params["person_key"]})
        return _resp(gr.get("narrative", ""), specs, "network",
                     params=params, audit_id=aid)

    if intent == "forecast":
        fc = forecast(params["district"], params["crime_sub_head"], con=con)
        if "error" in fc:
            aid = audit("chat", {"question": req.message, "tool": "forecast", "err": fc["error"]})
            return _resp(f"Not enough history to forecast {params['crime_sub_head']} in "
                         f"{params['district']}.", [], "forecast", params=params,
                         confidence="low", audit_id=aid)
        specs = [forecast_spec(fc, title=f"{params['crime_sub_head']} — {params['district']}")]
        nxt = fc["forecast"][0]
        answer = (f"Forecast for {params['crime_sub_head']} in {params['district']}: next week "
                  f"~{nxt['mean']:.0f} cases (backtest MAE {fc['backtest_mae']} vs seasonal-naive "
                  f"{fc['baseline_mae']}).")
        aid = audit("chat", {"question": req.message, "tool": "forecast", "params": params})
        return _resp(answer, specs, "forecast", params=params, audit_id=aid)

    if intent == "hotspots":
        h = hotspots(crime_sub_head=params.get("crime_sub_head"),
                     district=params.get("district"), con=con)
        specs = [map_spec(h["cells"][:50], title="Hotspots")]
        answer = (f"{len(h['cells'])} active cells; densest has {h['cells'][0]['count']} cases."
                  if h["cells"] else "No cases matched.")
        aid = audit("chat", {"question": req.message, "tool": "hotspots", "params": params})
        return _resp(answer, specs, "hotspots", row_count=len(h["cells"]),
                     params=params, audit_id=aid)

    if intent == "risk_rank":
        ranking = risk_rank(district=params.get("district"), con=con)
        cols = ["person", "score", "recency", "frequency", "gravity", "centrality"]
        rows = [[r["name"], r["score"], r["components"]["recency"], r["components"]["frequency"],
                 r["components"]["gravity"], r["components"]["centrality"]] for r in ranking]
        specs = [{"type": "table", "title": "Top repeat offenders",
                  "table": {"columns": cols, "rows": rows}}]
        answer = ("Top repeat offenders: "
                  + "; ".join(f"{r['name']} ({r['score']})" for r in ranking[:3]) + "."
                  if ranking else "No repeat offenders found.")
        aid = audit("chat", {"question": req.message, "tool": "risk_score", "n": len(ranking)})
        return _resp(answer, specs, "risk_score",
                     case_ids=ranking[0]["history_case_ids"] if ranking else [], audit_id=aid)

    return _run_sql_path(con, req, audit)
