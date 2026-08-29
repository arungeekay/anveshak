"""risk_score tool (contracts.md §7).

Components: recency, frequency, gravity, centrality. ADR-9: NO protected attributes
(religion/caste/occupation) are ever read, enforced by a unit test.
"""
from __future__ import annotations

import datetime as _dt
import math

from ..db import data_max_date, get_connection
from ..graph import engine as graph_engine

WEIGHTS = {"recency": 0.30, "frequency": 0.35, "gravity": 0.25, "centrality": 0.10}
RECENCY_TAU_DAYS = 912.0   # ~2.5y decay
FREQ_SATURATION = 4.0


def _as_date(v) -> _dt.date:
    # Duck-typed rather than isinstance(v, _dt.datetime): DuckDB's own datetime
    # subclasses (and a monkeypatched datetime in tests) must both normalise.
    if v is not None and hasattr(v, "date") and callable(v.date):
        return v.date()
    return v


def risk_score(person_key: str, con=None) -> dict:
    con = con or get_connection()
    rows = con.execute("""
        SELECT CaseMasterID, CrimeRegisteredDate, gravity
        FROM vw_accused_history WHERE person_key = ?
    """, [person_key]).fetchall()
    if not rows:
        return {"score": 0.0,
                "components": {k: 0.0 for k in WEIGHTS},
                "explanation": "No recorded case history.", "history_case_ids": []}

    case_ids = [int(r[0]) for r in rows]
    dates = [_as_date(r[1]) for r in rows]
    heinous = sum(1 for r in rows if r[2] == "Heinous")

    # Recency is measured from the data's last FIR, never the wall clock (F-02).
    days_since = (data_max_date(con) - max(dates)).days
    recency = math.exp(-days_since / RECENCY_TAU_DAYS)   # 1 = very recent
    frequency = min(1.0, len(case_ids) / FREQ_SATURATION)
    gravity = 1.0 if heinous > 0 else 0.5                # any heinous prior => high
    graph_engine.cache.ensure(con)
    centrality = float(graph_engine.cache.centrality.get(person_key, 0.0))

    comps = {"recency": round(recency, 3), "frequency": round(frequency, 3),
             "gravity": round(gravity, 3), "centrality": round(centrality, 3)}
    score = round(sum(WEIGHTS[k] * comps[k] for k in WEIGHTS), 3)
    explanation = (f"{len(case_ids)} prior case(s); most recent {days_since} days before "
                   f"the data cutoff; {heinous} heinous; network centrality "
                   f"{centrality:.2f}.")
    return {"score": score, "components": comps, "explanation": explanation,
            "history_case_ids": sorted(case_ids)}


def risk_rank(district: str | None = None, limit: int = 10, con=None) -> list[dict]:
    """Rank the most at-risk repeat offenders (optionally within a district)."""
    con = con or get_connection()
    sql = "SELECT person_key, full_name, COUNT(*) n FROM vw_accused_history"
    params: list = []
    if district:
        sql += " WHERE district = ?"
        params.append(district)
    sql += " GROUP BY person_key, full_name HAVING COUNT(*) >= 2 ORDER BY n DESC LIMIT 40"
    candidates = con.execute(sql, params).fetchall()
    ranked = []
    for pk, name, _n in candidates:
        r = risk_score(pk, con=con)
        ranked.append({"person_key": pk, "name": name, "score": r["score"],
                       "components": r["components"], "history_case_ids": r["history_case_ids"]})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:limit]
