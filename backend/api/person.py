"""Person 360 (contracts.md §9, FINALE_PLAN F-13).

Investigators think person-first, not query-first: "who is this man, what has he
done, who does he work with, how dangerous is he?" This composes tools we already
have — accused history, risk scoring, the CrimeGraph, similar cases — into the one
page an investigating officer would actually live in.

Every number still comes from a deterministic tool (ADR-2); this endpoint only
assembles them. Protected attributes are never included (ADR-9).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from ..auth import scope as scope_mod
from ..db import get_connection
from ..graph import engine as graph_engine
from ..tools.risk_score import risk_score

router = APIRouter()
log = logging.getLogger("anveshak.person")


@router.get("/api/person")
def search_person(q: str, request: Request, limit: int = 10) -> list[dict]:
    """Find people by (partial) name, most-connected first.

    Namesakes are common in police data, so the ordering matters: the person with
    the richest case history is the one an officer almost always means.
    """
    q = (q or "").strip()
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="query too short")
    con = get_connection()
    rows = con.execute("""
        SELECT h.person_key, MAX(h.full_name) AS name, COUNT(*) AS n_cases,
               MAX(h.CrimeRegisteredDate) AS last_seen
        FROM vw_accused_history h
        WHERE lower(h.full_name) LIKE lower(?)
        GROUP BY h.person_key
        ORDER BY n_cases DESC, last_seen DESC
        LIMIT ?
    """, [f"%{q}%", limit]).fetchall()
    sc = scope_mod.from_headers(request.headers)
    return [{"person_key": r[0], "name": scope_mod.mask_name(r[1], sc),
             "n_cases": int(r[2]),
             "last_seen": str(r[3])[:10] if r[3] else None} for r in rows]


@router.get("/api/person/{person_key}")
def person_profile(person_key: str, request: Request, graph_depth: int = 1) -> dict:
    """Everything known about one person: history, risk, network, timeline."""
    con = get_connection()
    sc = scope_mod.from_headers(request.headers)

    reg = con.execute(
        "SELECT person_key, full_name, dob, home_h3, notes FROM PersonRegistry "
        "WHERE person_key = ?", [person_key]).fetchone()
    cases = con.execute("""
        SELECT CaseMasterID, CrimeRegisteredDate, crime_sub_head, district,
               police_station, case_status, gravity, AccusedName, AgeYear
        FROM vw_accused_history WHERE person_key = ?
        ORDER BY CrimeRegisteredDate DESC
    """, [person_key]).fetchall()
    if not reg and not cases:
        raise HTTPException(status_code=404, detail=f"unknown person {person_key}")

    name = reg[1] if reg else (cases[0][7] if cases else person_key)
    case_rows = [{
        "case_id": int(c[0]), "date": str(c[1])[:10], "crime_sub_head": c[2],
        "district": c[3], "police_station": c[4], "case_status": c[5],
        "gravity": c[6],
    } for c in cases]

    risk = risk_score(person_key, con=con)

    # Aliases: other spellings the same person_key has been recorded under.
    aliases = sorted({c[7] for c in cases if c[7] and c[7] != name})

    # AgeYear is whatever each individual FIR recorded, and it varies across reports
    # for the same person (a real CCTNS problem too). Report the range rather than
    # picking one and implying a precision the data does not have.
    ages = sorted({int(c[8]) for c in cases if c[8] is not None})
    age_recorded = (f"{ages[0]}–{ages[-1]}" if len(ages) > 1 else
                    (str(ages[0]) if ages else None))

    districts = sorted({c["district"] for c in case_rows if c["district"]})
    sub_heads: dict[str, int] = {}
    for c in case_rows:
        if c["crime_sub_head"]:
            sub_heads[c["crime_sub_head"]] = sub_heads.get(c["crime_sub_head"], 0) + 1

    # Co-accused: people who appear in the same cases (the human network).
    co_accused = []
    if case_rows:
        ids = ",".join(str(c["case_id"]) for c in case_rows)
        co_accused = [{
            "person_key": r[0], "name": scope_mod.mask_name(r[1], sc),
            "shared_cases": int(r[2]),
        } for r in con.execute(f"""
            SELECT person_key, MAX(full_name), COUNT(DISTINCT CaseMasterID) n
            FROM vw_accused_history
            WHERE CaseMasterID IN ({ids}) AND person_key <> ?
            GROUP BY person_key ORDER BY n DESC LIMIT 10
        """, [person_key]).fetchall()]

    network = {}
    try:
        network = graph_engine.query(con, "ego_network",
                                     {"person_key": person_key, "depth": graph_depth})
    except Exception as exc:  # noqa: BLE001 - profile must render without the graph
        log.warning("ego_network failed for %s: %s", person_key, exc)

    arrests = con.execute("""
        SELECT COUNT(*) FROM ArrestSurrender ar
        JOIN AccusedPersonMap m ON m.AccusedMasterID = ar.AccusedMasterID
        WHERE m.person_key = ?
    """, [person_key]).fetchone()[0]

    return {
        "person_key": person_key,
        "name": scope_mod.mask_name(name, sc),
        "aliases": [scope_mod.mask_name(a, sc) for a in aliases],
        "age_recorded": age_recorded,   # range across FIRs; see note above
        "dob": str(reg[2])[:10] if reg and reg[2] else None,
        "home_h3": reg[3] if reg else None,
        "notes": reg[4] if reg else None,
        "risk": risk,
        "stats": {
            "total_cases": len(case_rows),
            "districts": districts,
            "crime_types": sorted(sub_heads.items(), key=lambda kv: -kv[1]),
            "arrests": int(arrests),
            "unsolved": sum(1 for c in case_rows
                            if c["case_status"] == "Under Investigation"),
        },
        "cases": case_rows,
        "co_accused": co_accused,
        "network": network,
    }
