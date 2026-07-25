"""Lightweight intent router for the conversational floor (contracts.md §2/§7).

Routes a message to a deterministic tool (linkage_scan/network/forecast/hotspots/
risk ranking) or falls back to run_sql (NL->SQL). Entity extraction matches known
districts/sub-heads/person names — no LLM needed, so routing is testable.
"""
from __future__ import annotations

from data_engine import masters as M

DISTRICTS = [d.name for d in M.DISTRICTS]
SUBHEADS = [s.name for s in M.SUBHEADS]

_LINKAGE = ("connected", "linked", "are these related", "same series", "serial",
            "same gang", "same person behind")
_FORECAST = ("forecast", "predict", "next target", "strike next", "where next",
             "ಮುಂದಿನ", "ಗುರಿ", "next window")
_HOTSPOT = ("hotspot", "hot spot", "concentrated", "cluster of", "map of", "where are most")
_RISK = ("repeat offender", "top offender", "habitual", "most active offender", "risk score")
_NETWORK = ("network", "connections", "associates", "linked to", "web of")


def _find(message: str, options: list[str]) -> str | None:
    low = message.lower()
    hits = [o for o in options if o.lower() in low]
    return max(hits, key=len) if hits else None


def resolve_person(con, message: str) -> str | None:
    low = message.lower()
    matches = [pk for pk, name in
               con.execute("SELECT person_key, full_name FROM PersonRegistry").fetchall()
               if name and name.lower() in low]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    # Name shared by several people -> pick the most-connected (the notable one),
    # so "Prakash Rao" resolves to the 14-case fraud hub, not a background namesake.
    ph = ",".join("?" for _ in matches)
    ranked = con.execute(
        f"SELECT person_key, COUNT(*) n FROM vw_accused_history WHERE person_key IN ({ph}) "
        f"GROUP BY person_key ORDER BY n DESC", matches).fetchall()
    return ranked[0][0] if ranked else matches[0]


def route(con, message: str) -> tuple[str, dict]:
    m = message.lower()
    if any(w in m for w in _LINKAGE):
        return "linkage", {}
    if any(w in m for w in _FORECAST):
        return "forecast", {"district": _find(message, DISTRICTS) or "Bengaluru City",
                            "crime_sub_head": _find(message, SUBHEADS) or "Chain Snatching"}
    if any(w in m for w in _HOTSPOT):
        return "hotspots", {"district": _find(message, DISTRICTS),
                            "crime_sub_head": _find(message, SUBHEADS)}
    if any(w in m for w in _RISK):
        return "risk_rank", {"district": _find(message, DISTRICTS)}
    if any(w in m for w in _NETWORK):
        pk = resolve_person(con, message)
        if pk:
            return "network", {"person_key": pk}
    return "run_sql", {}
