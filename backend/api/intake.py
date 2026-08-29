"""FIR intake + free-text similarity (contracts.md §9, FINALE_PLAN F-06).

The demo beat this exists for: an officer (or a judge on stage) files a *new* FIR in
their own words — typed or dictated in Kannada — and ANVESHAK embeds it at runtime,
re-runs linkage, and reports that it just joined an existing serial-crime series.
Detection stops being a claim and becomes an event the room witnesses.

Runtime embedding comes from the ONNX encoder (F-05), which is parity-checked
against the corpus vectors, so a new narrative is directly comparable with the
15,405 precomputed CaseMOVector rows (ADR-5).

Intake writes to the DuckDB analytical mirror; ADR-1 says the Data Store is the
system of record, so F-07 adds a best-effort Data Store write alongside this one.
"""
from __future__ import annotations

import datetime as _dt
import logging
import threading

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..audit import write_audit
from ..db import get_connection, reset_data_max_date
from ..embeddings import matrix
from ..embeddings.onnx_embedder import EmbedderUnavailable, embed_one
from ..linkage.store import store as series_store

router = APIRouter()
log = logging.getLogger("anveshak.intake")

# Allocating CaseMasterID as MAX+1 is a read-modify-write; serialise it (single
# AppSail worker) so two concurrent intakes cannot collide on the same id.
_intake_lock = threading.Lock()

# Defaults mirroring a real Chain Snatching FIR (see CaseMaster ids for SH-07):
# CrimeMajorHeadID 2 = Property Crimes, CaseStatusID 1 = Under Investigation.
DEFAULT_MAJOR_HEAD = 2
STATUS_UNDER_INVESTIGATION = 1
DEFAULT_CATEGORY = 1
DEFAULT_GRAVITY = 2

# The shipped corpus's highest CaseMasterID. Anything above this was filed through
# the demo intake, so /api/intake/reset can clear it without touching real data.
CORPUS_MAX_CASE_ID = 15405


class IntakeRequest(BaseModel):
    narrative: str = Field(min_length=20, max_length=4000)
    district: str
    police_station: str | None = None
    crime_sub_head: str | None = None
    occurred_on: str | None = None          # ISO date/datetime; defaults to data end
    lang: str = "en"


class SimilarByTextRequest(BaseModel):
    narrative: str = Field(min_length=10, max_length=4000)
    k: int = Field(default=5, ge=1, le=25)


def _resolve_unit(con, district: str, police_station: str | None) -> tuple[int, str, str]:
    """Resolve (UnitID, unit name, district name) from user-supplied names."""
    if police_station:
        row = con.execute("""
            SELECT u.UnitID, u.UnitName, d.DistrictName FROM Unit u
            JOIN District d ON d.DistrictID = u.DistrictID
            WHERE lower(u.UnitName) = lower(?) AND lower(d.DistrictName) = lower(?)
        """, [police_station, district]).fetchone()
        if row:
            return int(row[0]), row[1], row[2]
    row = con.execute("""
        SELECT u.UnitID, u.UnitName, d.DistrictName FROM Unit u
        JOIN District d ON d.DistrictID = u.DistrictID
        WHERE lower(d.DistrictName) = lower(?) ORDER BY u.UnitID LIMIT 1
    """, [district]).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail=f"unknown district: {district}")
    return int(row[0]), row[1], row[2]


def _resolve_sub_head(con, name: str | None) -> tuple[int, str]:
    """Resolve the crime sub-head; default to the demo's Chain Snatching."""
    if name:
        row = con.execute(
            "SELECT CrimeSubHeadID, CrimeHeadName FROM CrimeSubHead "
            "WHERE lower(CrimeHeadName) = lower(?)", [name]).fetchone()
        if row:
            return int(row[0]), row[1]
    row = con.execute(
        "SELECT CrimeSubHeadID, CrimeHeadName FROM CrimeSubHead "
        "WHERE CrimeHeadName = 'Chain Snatching'").fetchone()
    if not row:
        raise HTTPException(status_code=400, detail=f"unknown crime sub-head: {name}")
    return int(row[0]), row[1]


def _station_latlon(con, unit_id: int) -> tuple[float | None, float | None]:
    """A representative location for the station: the mean of its recent cases."""
    row = con.execute("""
        SELECT AVG(latitude), AVG(longitude) FROM CaseMaster
        WHERE PoliceStationID = ? AND latitude IS NOT NULL
    """, [unit_id]).fetchone()
    if row and row[0] is not None:
        return float(row[0]), float(row[1])
    return None, None


@router.post("/api/intake")
def intake(req: IntakeRequest, request: Request) -> dict:
    """Register a new FIR, embed it at runtime, and report which series it joins."""
    con = get_connection()
    unit_id, unit_name, district_name = _resolve_unit(con, req.district, req.police_station)
    sub_head_id, sub_head_name = _resolve_sub_head(con, req.crime_sub_head)

    # Date the FIR at the corpus end unless told otherwise, so it lands inside the
    # detectors' "recent" windows (F-02) rather than months in the future.
    from ..db import data_max_date
    if req.occurred_on:
        try:
            occurred = _dt.datetime.fromisoformat(req.occurred_on)
        except ValueError:
            raise HTTPException(status_code=400,
                                detail="occurred_on must be ISO format") from None
    else:
        occurred = _dt.datetime.combine(data_max_date(con), _dt.time(19, 30))

    lat, lon = _station_latlon(con, unit_id)

    try:
        vec = embed_one(req.narrative)
    except EmbedderUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="runtime embedding unavailable on this deployment") from exc

    from data_engine.mo import features_json

    with _intake_lock:
        case_id = int(con.execute(
            "SELECT COALESCE(MAX(CaseMasterID), 0) + 1 FROM CaseMaster").fetchone()[0])
        year = occurred.year
        crime_no = f"{unit_id:04d}{year}{case_id:08d}"
        con.execute("""
            INSERT INTO CaseMaster (CaseMasterID, CrimeNo, CaseNo, CrimeRegisteredDate,
                PolicePersonID, PoliceStationID, CaseCategoryID, GravityOffenceID,
                CrimeMajorHeadID, CrimeMinorHeadID, CaseStatusID, CourtID,
                IncidentFromDate, IncidentToDate, InfoReceivedPSDate,
                latitude, longitude, BriefFacts)
            VALUES (?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?, ?,?,?)
        """, [case_id, crime_no, str(case_id), occurred,
              None, unit_id, DEFAULT_CATEGORY, DEFAULT_GRAVITY,
              DEFAULT_MAJOR_HEAD, sub_head_id, STATUS_UNDER_INVESTIGATION, None,
              occurred, occurred, occurred,
              lat, lon, req.narrative])
        con.execute(
            "INSERT INTO CaseMOVector (CaseMasterID, embedding, mo_features, model) "
            "VALUES (?,?,?,?)",
            [case_id, [float(x) for x in vec],
             features_json(req.narrative, occurred, lat, lon), "onnx-minilm-runtime"])

    # ADR-1: the Data Store is the system of record, so the new FIR goes there too.
    # Best-effort — the mirror already holds it and the demo must not depend on the
    # console tables existing.
    from ..datastore import insert_case
    from ..llm.request_ctx import current_request
    current_request.set(request)
    datastore_written = insert_case({
        "CaseMasterID": case_id, "CrimeNo": crime_no,
        "CrimeRegisteredDate": occurred.isoformat(),
        "PoliceStationID": unit_id, "CrimeMinorHeadID": sub_head_id,
        "CaseStatusID": STATUS_UNDER_INVESTIGATION, "BriefFacts": req.narrative,
    })

    # Keep the in-memory search index and the date anchor consistent with the write.
    matrix.add(con, case_id, vec)
    reset_data_max_date()

    # Re-run discovery so the new FIR can join an existing series (this is the beat).
    t0 = _dt.datetime.now()
    series_store.rescan(con)
    rescan_ms = int((_dt.datetime.now() - t0).total_seconds() * 1000)
    joined = [h["series_id"] for h in series_store.containing(con, case_id)]

    write_audit(con, "demo", "SCRB", "intake",
                {"case_id": case_id, "district": district_name,
                 "police_station": unit_name, "sub_head": sub_head_name,
                 "joined_series": joined})
    log.info("intake case %s (%s/%s) joined %s", case_id, district_name, unit_name, joined)

    series_detail = []
    for sid in joined:
        h = series_store.get(con, sid)
        if h:
            series_detail.append({
                "series_id": sid, "crime_sub_head": h["crime_sub_head"],
                "confidence": h["confidence"], "case_count": len(h["case_ids"]),
                "districts": h["districts"]})

    return {
        "case_id": case_id,
        "crime_no": crime_no,
        "district": district_name,
        "police_station": unit_name,
        "crime_sub_head": sub_head_name,
        "registered_on": occurred.isoformat(timespec="seconds"),
        "embedded": True,
        "datastore_written": datastore_written,
        "joined_series": joined,
        "series": series_detail,
        "rescan_ms": rescan_ms,
    }


@router.post("/api/similar/by_text")
def similar_by_text(req: SimilarByTextRequest) -> dict:
    """Top-k historical cases most similar to an arbitrary narrative.

    Works on text that has never been seen before — paste any FIR and get the cases
    with the closest modus operandi.
    """
    con = get_connection()
    try:
        vec = embed_one(req.narrative)
    except EmbedderUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="runtime embedding unavailable on this deployment") from exc

    hits = matrix.search(con, vec, k=req.k)
    if not hits:
        return {"matches": []}
    ids = ",".join(str(cid) for cid, _ in hits)
    rows = {int(r[0]): r for r in con.execute(f"""
        SELECT CaseMasterID, CrimeNo, crime_sub_head, district, police_station,
               CrimeRegisteredDate, BriefFacts
        FROM vw_case_360 WHERE CaseMasterID IN ({ids})
    """).fetchall()}
    matches = []
    for cid, cos in hits:
        r = rows.get(cid)
        if not r:
            continue
        matches.append({
            "case_id": cid, "cosine": round(cos, 3), "crime_no": r[1],
            "crime_sub_head": r[2], "district": r[3], "police_station": r[4],
            "registered_on": str(r[5])[:10],
            "summary": (r[6] or "")[:200],
        })
    return {"matches": matches}


@router.post("/api/intake/reset")
def intake_reset() -> dict:
    """Remove demo-intake cases, restoring the pristine 15,405-case corpus.

    Run between rehearsals so the demo always starts from the same state (the
    series must read "15 cases" before the live intake grows it to 16). Only
    deletes ids above the shipped corpus max, so real data is never touched.
    """
    con = get_connection()
    with _intake_lock:
        n = con.execute(
            "SELECT COUNT(*) FROM CaseMaster WHERE CaseMasterID > ?",
            [CORPUS_MAX_CASE_ID]).fetchone()[0]
        con.execute("DELETE FROM CaseMOVector WHERE CaseMasterID > ?",
                    [CORPUS_MAX_CASE_ID])
        con.execute("DELETE FROM CaseMaster WHERE CaseMasterID > ?",
                    [CORPUS_MAX_CASE_ID])
    matrix.reset()
    matrix.ensure(con)
    reset_data_max_date()
    series_store.rescan(con)
    log.info("intake reset: removed %d demo case(s)", n)
    return {"removed": int(n), "cases": int(con.execute(
        "SELECT COUNT(*) FROM CaseMaster").fetchone()[0])}


@router.get("/api/masters")
def masters() -> dict:
    """District/station/sub-head lists for the intake form."""
    con = get_connection()
    districts = [r[0] for r in con.execute(
        "SELECT DistrictName FROM District ORDER BY DistrictName").fetchall()]
    stations: dict[str, list[str]] = {}
    for d, u in con.execute("""
        SELECT d.DistrictName, u.UnitName FROM Unit u
        JOIN District d ON d.DistrictID = u.DistrictID ORDER BY d.DistrictName, u.UnitName
    """).fetchall():
        stations.setdefault(d, []).append(u)
    sub_heads = [r[0] for r in con.execute(
        "SELECT CrimeHeadName FROM CrimeSubHead ORDER BY CrimeHeadName").fetchall()]
    return {"districts": districts, "police_stations": stations,
            "crime_sub_heads": sub_heads}
