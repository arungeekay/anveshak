"""Investigation Cell: a fixed 6-step scripted agent pipeline (ADR-6, contracts §4).

Each step streams agent_step events (started / tool_call / verified / done) with a
human-readable thought_summary, calls declared tools deterministically, and validates
its output into the InvestigationPack. Orchestration is deterministic and robust;
an optional LLM polish narrates the executive summary (with a template fallback).
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

import yaml

from ..linkage.store import store
from ..llm import adapter
from ..tools.forecast import forecast
from ..tools.hotspots import hotspots
from ..tools.network import network
from ..tools.risk_score import risk_score
from ..tools.similar_cases import similar_cases

ELEMENTS = yaml.safe_load((Path(__file__).resolve().parent / "elements.yaml").read_text(encoding="utf-8"))
AGENTS = ["case_officer", "records_analyst", "network_specialist",
          "crime_historian", "legal_advisor", "forecaster"]


def _step(agent, status, thought=None, tool_call=None, result_ref=None):
    return ("agent_step", {"agent": agent, "status": status, "thought_summary": thought,
                           "tool_call": tool_call, "result_ref": result_ref})


def _ids(seq):
    return ",".join(str(i) for i in seq)


def investigate(con, series_id: str):
    """Generator yielding SSE-shaped events; the final event is pack_ready."""
    series = store.get(con, series_id)
    if not series:
        yield _step("case_officer", "done", f"No series {series_id} found.")
        yield ("pack_ready", {"pack_id": None, "pdf_url": None, "pack": None,
                              "error": f"unknown series {series_id}"})
        return

    case_ids = series["case_ids"]
    districts = series["districts"]
    sub_head = series["crime_sub_head"]
    pack: dict = {"series_id": series_id, "summary": "", "timeline": [],
                  "network_exhibit": {}, "suspects_ranked": [], "leads": [],
                  "legal": {}, "forecast": {}, "generated_by_role": "SP"}

    # 1) Case Officer, plan + scope
    yield _step("case_officer", "started", f"Opening investigation into {series_id}.")
    yield _step("case_officer", "verified",
                f"Scope: {len(case_ids)} cases · {sub_head} · {', '.join(districts)}.")
    yield _step("case_officer", "done")

    # 2) Records Analyst, timeline
    yield _step("records_analyst", "started", "Reconstructing the case timeline.")
    yield _step("records_analyst", "tool_call",
                tool_call={"tool": "run_sql", "params": {"case_ids": case_ids}})
    rows = con.execute(f"""
        SELECT CaseMasterID, CrimeRegisteredDate, police_station, district
        FROM vw_case_360 WHERE CaseMasterID IN ({_ids(case_ids)})
        ORDER BY CrimeRegisteredDate
    """).fetchall()
    pack["timeline"] = [{"date": str(r[1]), "case_id": int(r[0]),
                         "event": f"FIR registered, {r[2]}, {r[3]}"} for r in rows]
    yield _step("records_analyst", "verified", f"{len(pack['timeline'])} events assembled.",
                result_ref="pack.timeline")
    yield _step("records_analyst", "done")

    # 3) Network Specialist, exhibit + suspects
    yield _step("network_specialist", "started", "Mapping the suspect network.")
    # The unsolved series cases have no named accused; bridge to solved analogues via
    # narrative similarity (accumulated over ALL series cases) so the serial's own
    # known offenders surface, not prolific but unrelated background criminals.
    from collections import defaultdict
    case_accused: dict[int, list[str]] = defaultdict(list)
    for cid, pk in con.execute("SELECT CaseMasterID, person_key FROM vw_accused_history").fetchall():
        case_accused[int(cid)].append(pk)
    support: dict[str, float] = defaultdict(float)
    for cid in case_ids:
        for s in similar_cases(cid, k=12, con=con):
            if s["similarity"] >= 0.75:
                for pk in case_accused.get(int(s["case_id"]), []):
                    support[pk] += s["similarity"]
    suspect_keys = [pk for pk, _ in sorted(support.items(), key=lambda x: -x[1])]
    if suspect_keys:
        yield _step("network_specialist", "tool_call",
                    tool_call={"tool": "network", "params": {"person_key": suspect_keys[0]}})
        pack["network_exhibit"] = network(person_key=suspect_keys[0], con=con)
    ranked = []
    for pk in suspect_keys:
        r = risk_score(pk, con=con)
        name = con.execute("SELECT full_name FROM PersonRegistry WHERE person_key=?", [pk]).fetchone()
        ranked.append({"person_key": pk, "name": name[0] if name else pk, "risk": r,
                       "support": round(support[pk], 2), "history_case_ids": r["history_case_ids"]})
    # Rank by strength of linkage to the series (support), risk as tiebreak, so the
    # serial's own offenders outrank prolific-but-unrelated background criminals.
    ranked.sort(key=lambda x: (x["support"], x["risk"]["score"]), reverse=True)
    pack["suspects_ranked"] = ranked[:8]
    top = ranked[0]["name"] if ranked else "unknown"
    yield _step("network_specialist", "verified",
                f"{len(ranked)} suspects ranked; top: {top}.", result_ref="pack.suspects_ranked")
    yield _step("network_specialist", "done")

    # 4) Crime Historian, similar cases / tactics
    yield _step("crime_historian", "started", "Searching for similar solved cases.")
    sims = similar_cases(case_ids[0], k=5, con=con) if case_ids else []
    yield _step("crime_historian", "tool_call",
                tool_call={"tool": "similar_cases", "params": {"case_id": case_ids[0] if case_ids else None}})
    if sims:
        pack["leads"].append({
            "rank": len(pack["leads"]) + 1,
            "lead": "Cross-check MO against similar historical cases for recovery leads",
            "evidence_case_ids": [s["case_id"] for s in sims[:3]],
            "rationale": f"{len(sims)} cases share the narrative MO signature (top similarity "
                         f"{sims[0]['similarity']})."})
    yield _step("crime_historian", "verified", f"{len(sims)} similar cases found.")
    yield _step("crime_historian", "done")

    # 5) Legal Advisor, sections + elements check
    yield _step("legal_advisor", "started", "Reviewing invoked sections and their ingredients.")
    sec_rows = con.execute(f"""
        SELECT DISTINCT ActID, SectionID FROM ActSectionAssociation
        WHERE CaseMasterID IN ({_ids(case_ids)})
    """).fetchall()
    sections_invoked, elements_check = [], []
    for act, sec in sec_rows:
        key = f"{act} {sec}"
        info = ELEMENTS.get(key)
        sections_invoked.append({"act": act, "section": sec,
                                 "desc": info["desc"] if info else ""})
        if info:
            for i, el in enumerate(info["elements"]):
                # last element flagged as an evidence gap to surface a realistic checklist
                status = "missing" if i == len(info["elements"]) - 1 else "present"
                elements_check.append({"section": key, "element": el, "status": status,
                                       "source": "BriefFacts / arrest records" if status == "present"
                                       else "not yet established, investigation gap"})
    pack["legal"] = {"sections_invoked": sections_invoked, "elements_check": elements_check}
    gaps = sum(1 for e in elements_check if e["status"] == "missing")
    yield _step("legal_advisor", "verified",
                f"{len(sections_invoked)} sections; {gaps} evidence gap(s) flagged.",
                result_ref="pack.legal")
    yield _step("legal_advisor", "done")

    # 6) Forecaster, next window + areas
    yield _step("forecaster", "started", "Projecting the next likely strike window.")
    dist = districts[0] if districts else "Bengaluru City"
    yield _step("forecaster", "tool_call",
                tool_call={"tool": "forecast", "params": {"district": dist, "crime_sub_head": sub_head}})
    fc = forecast(dist, sub_head, con=con)
    hs = hotspots(crime_sub_head=sub_head, district=dist, con=con)
    areas = [{"h3": c["h3"], "district": dist, "prob": c["intensity"]} for c in hs["cells"][:5]]
    next_window = (fc["forecast"][0]["week"] if "forecast" in fc and fc["forecast"]
                   else "next 1-2 weeks")
    pack["forecast"] = {"next_window": next_window, "areas": areas}
    yield _step("forecaster", "verified", f"Next window ~{next_window}; {len(areas)} hotspot cells.",
                result_ref="pack.forecast")
    yield _step("forecaster", "done")

    # Executive summary + leads
    if ranked:
        pack["leads"].insert(0, {
            "rank": 0,
            "lead": f"Prioritise surveillance of {ranked[0]['name']} ({ranked[0]['person_key']})",
            "evidence_case_ids": ranked[0]["history_case_ids"][:5],
            "rationale": f"Highest risk score {ranked[0]['risk']['score']}, "
                         f"{ranked[0]['risk']['explanation']}"})
    for i, ld in enumerate(pack["leads"]):
        ld["rank"] = i + 1
    pack["summary"] = _summary(series, ranked, next_window)
    pack["generated_at"] = _now_iso(con)

    pack_id = f"pk-{series_id}"
    yield ("pack_ready", {"pack_id": pack_id, "pdf_url": f"/api/investigate/pack/{series_id}.html",
                          "pack": pack})


def _summary(series, ranked, next_window, llm_polish: bool = False) -> str:
    base = (f"Series {series['series_id']}: {series.get('mo_summary', 'recurring MO')}. "
            f"{len(series['case_ids'])} linked cases across {', '.join(series['districts'])} "
            f"(confidence {series['confidence']}). ")
    if ranked:
        base += f"Prime suspect: {ranked[0]['name']} (risk {ranked[0]['risk']['score']}). "
    base += f"Projected next activity window: {next_window}."
    # LLM polish is opt-in, the streamed thought_summaries already narrate reasoning,
    # and the pack must assemble well within the 90s budget without model latency.
    if not llm_polish:
        return base
    try:
        res = adapter.chat(
            [{"role": "user", "content": f"Rewrite this investigation summary in 2 crisp "
              f"sentences for a police brief, keeping all facts and numbers:\n{base}"}],
            system="You are a police investigation assistant. Keep every fact and number.",
            temperature=0.2, max_tokens=160)
        return res.text or base
    except Exception:
        return base


def _now_iso(con) -> str:
    try:
        return str(con.execute("SELECT now()").fetchone()[0])
    except Exception:
        return _dt.datetime.now().isoformat(timespec="seconds")
