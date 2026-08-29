"""Idempotent Data Store loader (ADR-1 · T06): CSV exports -> Catalyst Data Store.

Data Store is the system of record; the DuckDB mirror is derived from it. Tables must
exist in the console first (Data Store defines column types there, see
docs/catalyst/datastore.md). Run inside AppSail (auth context) or standalone with
admin scope + Catalyst credentials.

Two paths:
  1. SDK (this script): chunked `insert_rows`, optional --truncate via ZCQL DELETE.
  2. CLI bulk (recommended for 15k): `catalyst ds:import build/csv/<Table>.csv`.

Usage: python -m data_engine.load_datastore [--csv-dir build/csv] [--truncate]
       [--only CaseMaster,District,...]
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

CHUNK = 100
# Load order respects FK dependencies (masters first, then transactional).
LOAD_ORDER = [
    "State", "District", "UnitType", "Unit", "Rank", "Designation", "Employee", "Court",
    "Act", "Section", "CrimeHead", "CrimeSubHead", "CrimeHeadActSection", "CaseCategory",
    "GravityOffence", "CaseStatusMaster", "OccupationMaster", "ReligionMaster",
    "CasteMaster", "DistrictIndicators", "PersonRegistry", "CaseMaster",
    "ComplainantDetails", "Victim", "Accused", "AccusedPersonMap", "ActSectionAssociation",
    "ArrestSurrender", "inv_arrestsurrenderaccused", "Inv_OccuranceTime",
    "ChargesheetDetails", "CaseMOVector", "AuditLog",
]


def _rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def load(csv_dir: str = "build/csv", truncate: bool = False, only: list[str] | None = None) -> None:
    import zcatalyst_sdk  # imported here so the module is importable without the SDK

    app = zcatalyst_sdk.initialize(scope="admin")
    ds = app.datastore()
    zcql = app.zcql()
    base = Path(csv_dir)
    tables = [t for t in LOAD_ORDER if (not only or t in only)]

    for name in tables:
        path = base / f"{name}.csv"
        if not path.exists():
            print(f"skip {name}: {path} missing")
            continue
        rows = _rows(path)
        # CaseMOVector.embedding is a float list -> store as JSON text.
        if name == "CaseMOVector":
            for r in rows:
                if isinstance(r.get("embedding"), str) and r["embedding"].startswith("["):
                    r["embedding"] = json.dumps(json.loads(r["embedding"]))
        if truncate:
            try:
                zcql.execute_query(f"DELETE FROM {name}")
            except Exception as exc:  # table may be empty / not exist yet
                print(f"  truncate {name} skipped: {exc}")
        table = ds.table(name)
        n = 0
        for chunk in _chunks(rows, CHUNK):
            table.insert_rows(chunk)
            n += len(chunk)
        print(f"loaded {name}: {n} rows")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", default="build/csv")
    ap.add_argument("--truncate", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    only = [t for t in args.only.split(",") if t] or None
    load(args.csv_dir, args.truncate, only)


if __name__ == "__main__":
    main()
