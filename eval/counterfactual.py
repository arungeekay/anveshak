"""Retrospective replay: when would ANVESHAK have caught the series? (F-11)

Runs the real linkage engine against the corpus truncated to successive dates and
finds the earliest point at which the series becomes detectable. The output answers
the question a police jury actually cares about — *what would this have changed?* —
with a number computed by our own engine rather than asserted in a slide.

Honest by construction: it is a retrospective replay on synthetic data, the method
is recorded in the artefact, and if the answer is unimpressive we report that.

    python -m eval.counterfactual                 # SH-07
    python -m eval.counterfactual --series SH-03

Writes backend/static_data/counterfactual_<series>.json (committed — derived data).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path

import duckdb

from backend.linkage import engine as linkage_engine

OUT_DIR = Path("backend/static_data")
DB_PATH = "build/anveshak.duckdb"

# A series is "detectable" once the engine clusters at least this many of its cases
# together with at least this confidence — i.e. enough for an officer to act on.
MIN_MEMBERS = 4
MIN_CONFIDENCE = 0.70


def _truth_case_ids(con, series_id: str) -> list[int]:
    """The series' member cases, ordered by registration date."""
    from backend.linkage.store import store
    h = store.get(con, series_id)
    if not h:
        raise SystemExit(f"unknown series {series_id}")
    ids = ",".join(str(i) for i in h["case_ids"])
    rows = con.execute(f"""
        SELECT CaseMasterID, CrimeRegisteredDate, district, police_station
        FROM vw_case_360 WHERE CaseMasterID IN ({ids})
        ORDER BY CrimeRegisteredDate
    """).fetchall()
    return [(int(r[0]), r[1], r[2], r[3]) for r in rows], h


def _detectable_at(db_path: str, cutoff: _dt.datetime, member_ids: set[int]) -> dict | None:
    """Run discovery on data truncated at `cutoff`; return the matching hypothesis.

    Uses a private in-memory copy so the shipped mirror is never modified.
    """
    con = duckdb.connect(":memory:")
    con.execute(f"ATTACH '{db_path}' AS src (READ_ONLY)")
    # Copy every table, truncating the case table at the cutoff date.
    tables = [r[0] for r in con.execute(
        "SELECT table_name FROM src.information_schema.tables "
        "WHERE table_type='BASE TABLE'").fetchall()]
    for t in tables:
        if t == "CaseMaster":
            con.execute(f'CREATE TABLE "{t}" AS SELECT * FROM src."{t}" '
                        f"WHERE CrimeRegisteredDate <= ?", [cutoff])
        else:
            con.execute(f'CREATE TABLE "{t}" AS SELECT * FROM src."{t}"')
    # Recreate the views the engine reads.
    from data_engine.build import create_views
    create_views(con)
    con.execute("DETACH src")

    for h in linkage_engine.discover(con):
        overlap = member_ids & set(h["case_ids"])
        if len(overlap) >= MIN_MEMBERS and h["confidence"] >= MIN_CONFIDENCE:
            return {"confidence": h["confidence"], "found": sorted(overlap),
                    "cluster_size": len(h["case_ids"])}
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="SH-07")
    ap.add_argument("--db", default=DB_PATH)
    args = ap.parse_args()

    con = duckdb.connect(args.db, read_only=True)
    import backend.db as bdb
    bdb._conn = con  # the store reads through backend.db
    cases, hyp = _truth_case_ids(con, args.series)
    member_ids = {c[0] for c in cases}
    print(f"{args.series}: {len(cases)} cases, "
          f"{cases[0][1].date()} → {cases[-1][1].date()}")

    # Step through the series' own case dates: after the Nth case, is it visible?
    detected_at = None
    for n, (cid, dt, district, ps) in enumerate(cases, start=1):
        if n < MIN_MEMBERS:
            continue
        hit = _detectable_at(args.db, dt, member_ids)
        status = (f"conf {hit['confidence']:.2f}, {len(hit['found'])} linked"
                  if hit else "not yet detectable")
        print(f"  after case #{n:2} ({dt.date()}, {district}): {status}")
        if hit and detected_at is None:
            detected_at = {"ordinal": n, "case_id": cid, "date": str(dt.date()),
                           "district": district, "police_station": ps, **hit}
            break

    if not detected_at:
        print("\nNot detectable before the full series — reporting honestly, no banner.")
        return 1

    after = [c for c in cases if c[1] > _dt.datetime.fromisoformat(detected_at["date"])]
    districts_after = sorted({c[2] for c in after})
    artefact = {
        "series_id": args.series,
        "total_cases": len(cases),
        "detectable_at_case": detected_at["ordinal"],
        "detected_on": detected_at["date"],
        "detected_confidence": round(detected_at["confidence"], 3),
        "cases_after_detection": len(after),
        "districts_after_detection": districts_after,
        "first_case_on": str(cases[0][1].date()),
        "last_case_on": str(cases[-1][1].date()),
        "days_of_exposure": (cases[-1][1] - _dt.datetime.fromisoformat(
            detected_at["date"])).days,
        "method": (f"Retrospective replay: the linkage engine was re-run on the "
                   f"corpus truncated at each of the series' own case dates. "
                   f"'Detectable' means >= {MIN_MEMBERS} of its cases clustered "
                   f"together with confidence >= {MIN_CONFIDENCE}. Synthetic data; "
                   f"no real case is implied."),
        "generated_on": _dt.date.today().isoformat(),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"counterfactual_{args.series}.json"
    out.write_text(json.dumps(artefact, indent=2), encoding="utf-8")

    print(f"\nDetectable at case #{artefact['detectable_at_case']} "
          f"({artefact['detected_on']}).")
    print(f"{artefact['cases_after_detection']} further offences across "
          f"{len(districts_after)} district(s) followed over "
          f"{artefact['days_of_exposure']} days.")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
