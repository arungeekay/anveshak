"""Patrol Plan (contracts.md §9, FINALE_PLAN F-14).

Police leadership's standing complaint about crime analytics is "so what do I
actually *do* tonight?". This turns the signals ANVESHAK already computes -
overnight leads, recent concentrations, series geography, weekly forecasts, into a
ranked deployment card per district: which station, which window, which beats, and
why.

Honest framing, stated in the payload: it is a heuristic composition of tool
outputs, not an optimiser. Every item carries the tools it came from (ADR-2), so an
officer can audit the reasoning before acting on it.
"""
from __future__ import annotations

import datetime as _dt
import logging
from collections import Counter

from fastapi import APIRouter, HTTPException

from ..db import data_max_date, get_connection
from ..linkage.store import store as series_store
from ..patrol.store import leads_store

router = APIRouter()
log = logging.getLogger("anveshak.patrol_plan")

RECENT_DAYS = 30
# Discovery also returns large background clusters (an MO common to hundreds of
# ordinary cases). They are not rings to deploy against, so the plan ignores them.
MAX_SERIES_CASES = 40
MIN_SERIES_CONF = 0.75
# Peak offence windows by time-of-day bucket, from the incident hour distribution.
_WINDOWS = {
    "night": "00:00–05:00", "morning": "06:00–11:00",
    "afternoon": "12:00–16:00", "evening": "17:00–20:00",
    "late_evening": "21:00–23:59",
}


def _peak_window(con, unit_name: str, sub_head: str) -> str:
    """The time band this offence actually clusters in at this station."""
    rows = con.execute("""
        SELECT hour(IncidentFromDate) h, COUNT(*) n FROM vw_case_360
        WHERE police_station = ? AND crime_sub_head = ? AND IncidentFromDate IS NOT NULL
        GROUP BY 1 ORDER BY n DESC LIMIT 3
    """, [unit_name, sub_head]).fetchall()
    if not rows:
        return _WINDOWS["evening"]
    from data_engine.mo import tod_bucket
    bucket = Counter(tod_bucket(int(r[0])) for r in rows).most_common(1)[0][0]
    return _WINDOWS.get(bucket, _WINDOWS["evening"])


@router.get("/api/patrol/plan")
def patrol_plan(district: str, limit: int = 5) -> dict:
    """A ranked, explainable deployment plan for one district."""
    con = get_connection()
    ok = con.execute("SELECT COUNT(*) FROM District WHERE lower(DistrictName)=lower(?)",
                     [district]).fetchone()[0]
    if not ok:
        raise HTTPException(status_code=400, detail=f"unknown district: {district}")

    anchor = data_max_date(con)
    since = anchor - _dt.timedelta(days=RECENT_DAYS)
    items: dict[str, dict] = {}

    def _item(ps: str) -> dict:
        return items.setdefault(ps, {
            "police_station": ps, "district": district, "priority": 0.0,
            "reasons": [], "sources": [], "case_ids": [],
            # offence -> how much it contributed, so "focus" reflects what actually
            # drove the ranking rather than whatever sorts first alphabetically.
            "focus_weight": Counter(),
        })

    # 1) Overnight leads for this district, the strongest signal we have.
    for ld in leads_store.ensure(con):
        if (ld.get("district") or "").lower() != district.lower():
            continue
        title = ld.get("title", "")
        ps = title.split("-")[-1].strip() if "-" in title else None
        if not ps:
            continue
        it = _item(ps)
        ev = ld.get("evidence") or {}
        weight = 3.0 * float(ld.get("confidence", 0.5))
        it["priority"] += weight
        it["reasons"].append(title)
        it["sources"].append(f"night_patrol:{ld.get('type')}")
        it["case_ids"] += (ev.get("case_ids") or [])[:20]
        # The offence named in the lead title, e.g. "House Burglary (Night) 18.3x ...".
        offence = title.split(", ")[0].split(" 1")[0].split(" grew")[0].strip()
        if offence:
            it["focus_weight"][offence] += weight

    # 2) Recent concentration by station and offence type.
    for ps, sub, n in con.execute("""
        SELECT police_station, crime_sub_head, COUNT(*) n FROM vw_case_360
        WHERE district = ? AND CrimeRegisteredDate > CAST(? AS DATE)
        GROUP BY 1, 2 HAVING COUNT(*) >= 3 ORDER BY n DESC LIMIT 12
    """, [district, since]).fetchall():
        it = _item(ps)
        weight = min(2.0, n / 5.0)
        it["priority"] += weight
        it["focus_weight"][sub] += weight
        it["reasons"].append(f"{n} {sub} cases in the last {RECENT_DAYS} days")
        it["sources"].append("run_sql:recent_concentration")

    # 3) Active series touching this district, where the next strike is expected.
    for h in series_store.all(con):
        if district not in (h.get("districts") or []):
            continue
        # Only genuine serial-crime signals. The discovery pass also surfaces large
        # background clusters (hundreds of cases sharing a common MO); those describe
        # ordinary crime volume, not a ring worth deploying against, and letting them
        # in swamps both the score and the reasoning.
        if len(h["case_ids"]) > MAX_SERIES_CASES or h.get("confidence", 0) < MIN_SERIES_CONF:
            continue
        ids = ",".join(str(i) for i in h["case_ids"])
        rows = con.execute(f"""
            SELECT police_station, COUNT(*) n FROM vw_case_360
            WHERE CaseMasterID IN ({ids}) AND district = ?
            GROUP BY 1 ORDER BY n DESC LIMIT 2
        """, [district]).fetchall()
        for ps, n in rows:
            it = _item(ps)
            weight = 2.5 * float(h.get("confidence", 0.5))
            it["priority"] += weight
            it["focus_weight"][h["crime_sub_head"]] += weight
            it["reasons"].append(
                f"series {h['series_id']} ({h['crime_sub_head']}), {n} of its "
                f"{len(h['case_ids'])} cases here, confidence "
                f"{h['confidence']:.2f}")
            it["sources"].append(f"linkage:{h['series_id']}")

    if not items:
        return {"district": district, "generated_for": str(anchor), "items": [],
                "note": "no active signals for this district in the recent window"}

    ranked = sorted(items.values(), key=lambda x: -x["priority"])[:limit]
    out = []
    for it in ranked:
        top_focus = [f for f, _ in it["focus_weight"].most_common(3)]
        sub = top_focus[0] if top_focus else "All offences"
        out.append({
            "police_station": it["police_station"],
            "district": district,
            "window": _peak_window(con, it["police_station"], sub),
            "focus": top_focus or ["All offences"],
            "priority": round(it["priority"], 2),
            "reasons": it["reasons"][:4],
            "sources": sorted(set(it["sources"])),
            "case_ids": sorted(set(it["case_ids"]))[:20],
        })

    return {
        "district": district,
        "generated_for": str(anchor),
        "items": out,
        "method": ("Heuristic composition of Night-Patrol leads, 30-day case "
                   "concentration and active series geography. Peak windows come "
                   "from each station's own incident-hour distribution. This assists "
                   "allocation decisions; it does not replace them."),
    }
