"""Night Patrol detectors (contracts.md §5): spike, series_growth, repeat_offender.

Runs against the DuckDB mirror and emits ranked LeadCards. The Cron entrypoint,
Signals and Mail digest are the deferred Catalyst pieces; POST /api/leads/run drives
the detectors synchronously for the demo.
"""
from __future__ import annotations

import datetime as _dt
import math

import h3

from ..linkage.store import store

DATA_END = _dt.date(2026, 7, 20)
WINDOW_DAYS = 14
START = _dt.date(2023, 1, 1)


def _haversine(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _spike(con) -> list[dict]:
    cutoff = DATA_END - _dt.timedelta(days=WINDOW_DAYS)
    weeks_hist = max((cutoff - START).days / 7.0, 1.0)
    combos = con.execute("""
        SELECT police_station, district, crime_sub_head, COUNT(*) n
        FROM vw_case_360 WHERE CrimeRegisteredDate > CAST(? AS DATE)
        GROUP BY 1, 2, 3 HAVING COUNT(*) >= 6
    """, [cutoff]).fetchall()
    leads = []
    for ps, dist, sub, recent in combos:
        hist = con.execute("""
            SELECT COUNT(*) FROM vw_case_360 WHERE police_station=? AND crime_sub_head=?
            AND CrimeRegisteredDate <= CAST(? AS DATE)
        """, [ps, sub, cutoff]).fetchone()[0]
        base_rate = hist / weeks_hist
        recent_rate = recent / (WINDOW_DAYS / 7.0)
        std = max(math.sqrt(base_rate), 0.5)
        z = (recent_rate - base_rate) / std
        if z < 3:
            continue
        cids = [int(r[0]) for r in con.execute("""
            SELECT CaseMasterID FROM vw_case_360 WHERE police_station=? AND crime_sub_head=?
            AND CrimeRegisteredDate > CAST(? AS DATE)
        """, [ps, sub, cutoff]).fetchall()]
        ratio = recent_rate / max(base_rate, 0.3)
        leads.append({
            "type": "spike",
            "title": f"{sub} {ratio:.1f}x baseline — {ps}",
            "evidence": {"metric": "stl_residual_z", "value": round(z, 1),
                         "window": f"last {WINDOW_DAYS}d", "case_ids": cids},
            "confidence": round(min(0.95, 0.6 + z / 30), 2),
            "suggested_action": f"Increase night patrols and pickets around {ps} for the next 14 days.",
            "district": dist, "_z": z,
        })
    leads.sort(key=lambda x: x["_z"], reverse=True)
    return leads[:8]


def _series_growth(con) -> list[dict]:
    cutoff = DATA_END - _dt.timedelta(days=WINDOW_DAYS)
    leads = []
    for s in store.all(con):
        recent = con.execute(f"""
            SELECT COUNT(*) FROM vw_case_360
            WHERE CaseMasterID IN ({','.join(str(i) for i in s['case_ids'])})
            AND CrimeRegisteredDate > CAST(? AS DATE)
        """, [cutoff]).fetchone()[0]
        if recent >= 2:
            leads.append({
                "type": "series_growth",
                "title": f"Series {s['series_id']} grew by {recent} cases",
                "evidence": {"metric": "new_cases_14d", "value": recent,
                             "window": f"last {WINDOW_DAYS}d", "case_ids": s["case_ids"]},
                "confidence": s["confidence"],
                "suggested_action": f"Escalate {s['series_id']} ({s['crime_sub_head']}) to a special team.",
                "district": s["districts"][0] if s["districts"] else "",
            })
    return leads


def _repeat_offender(con) -> list[dict]:
    cutoff = DATA_END - _dt.timedelta(days=45)
    inactive_before = DATA_END - _dt.timedelta(days=60)
    # Only offenders who were actually arrested (i.e. could have been released).
    arrested = {r[0] for r in con.execute("""
        SELECT DISTINCT m.person_key FROM ArrestSurrender ar
        JOIN AccusedPersonMap m ON m.AccusedMasterID = ar.AccusedMasterID
    """).fetchall()}
    # Offenders with >=3 priors, a home cell, and no very-recent attributed case.
    offenders = con.execute("""
        SELECT h.person_key, pr.home_h3, MAX(h.CrimeRegisteredDate) last_seen, COUNT(*) n
        FROM vw_accused_history h JOIN PersonRegistry pr ON pr.person_key = h.person_key
        WHERE pr.home_h3 IS NOT NULL
        GROUP BY h.person_key, pr.home_h3
        HAVING COUNT(*) >= 3 AND MAX(h.CrimeRegisteredDate) <= CAST(? AS DATE)
    """, [inactive_before]).fetchall()
    leads = []
    for pk, home_h3, _last, _n in offenders:
        if pk not in arrested:
            continue
        # sub-heads the offender has a real pattern in (>=2 priors)
        subs = [r[0] for r in con.execute(
            "SELECT crime_sub_head FROM vw_accused_history WHERE person_key=? "
            "GROUP BY crime_sub_head HAVING COUNT(*) >= 2", [pk]
        ).fetchall()]
        if not subs:
            continue
        hlat, hlon = h3.cell_to_latlng(home_h3)
        placeholders = ",".join("?" for _ in subs)
        fresh = con.execute(f"""
            SELECT CaseMasterID, latitude, longitude FROM vw_case_360
            WHERE case_status='Under Investigation' AND accused_count=0
            AND crime_sub_head IN ({placeholders})
            AND CrimeRegisteredDate > CAST(? AS DATE)
        """, [*subs, cutoff]).fetchall()
        near = [int(c) for c, lat, lon in fresh
                if lat is not None and _haversine(hlat, hlon, lat, lon) <= 3.0]
        if len(near) >= 4:
            name = con.execute("SELECT full_name FROM PersonRegistry WHERE person_key=?", [pk]).fetchone()
            leads.append({
                "type": "repeat_offender",
                "title": f"Possible re-offending by {name[0] if name else pk} near home turf",
                "evidence": {"metric": "matching_unsolved_within_3km", "value": len(near),
                             "window": "last 45d", "case_ids": near},
                "confidence": round(min(0.9, 0.6 + 0.1 * len(near)), 2),
                "suggested_action": f"Question {name[0] if name else pk}; verify alibi for the "
                                    f"{len(near)} unsolved cases near their residence.",
                "district": "Bengaluru City",
            })
    return leads


def run_detectors(con) -> list[dict]:
    leads = _spike(con) + _repeat_offender(con) + _series_growth(con)
    for i, ld in enumerate(leads, 1):
        ld.pop("_z", None)
        ld["lead_id"] = f"L-{i}"
        ld["created_at"] = DATA_END.isoformat()
    return leads
