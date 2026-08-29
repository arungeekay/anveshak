"""Print the Data Store table definitions to create in the Catalyst console (F-07).

Catalyst Data Store tables and their column types are defined in the console, not
by SQL (docs/catalyst/datastore.md). This reads the real schema from the built
DuckDB mirror and prints exactly what to create, so the console work is mechanical
rather than guesswork.

    python scripts/datastore_schema.py           # human-readable
    python scripts/datastore_schema.py --csv     # CSV paths for `catalyst ds:import`
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.datastore import CORE_TABLES  # noqa: E402

DB_PATH = "build/anveshak.duckdb"
CSV_DIR = Path("build/csv")

# DuckDB type -> Catalyst Data Store column type (console dropdown values).
TYPE_MAP = {
    "BIGINT": "BigInt", "INTEGER": "Int", "HUGEINT": "BigInt",
    "DOUBLE": "Double", "FLOAT": "Double", "DECIMAL": "Double",
    "VARCHAR": "Text", "BOOLEAN": "Boolean",
    "TIMESTAMP": "DateTime", "TIMESTAMP_NS": "DateTime", "DATE": "Date",
}


def catalyst_type(duck_type: str) -> str:
    base = duck_type.upper().split("(")[0].strip()
    return TYPE_MAP.get(base, "Text")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--csv", action="store_true", help="print ds:import commands")
    args = ap.parse_args()

    con = duckdb.connect(args.db, read_only=True)
    print("Catalyst Data Store, tables to create in the console")
    print("(Console → Data Store → New Table. Every table also gets ROWID + "
          "system columns automatically.)\n")

    for name in CORE_TABLES:
        cols = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position", [name]).fetchall()
        if not cols:
            print(f"  ! {name}: not present in the mirror, skipping\n")
            continue
        rows = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        print(f"TABLE {name}   ({rows:,} rows to import)")
        for col, dtype in cols:
            print(f"    {col:24} {catalyst_type(dtype):10}  (duckdb: {dtype})")
        print()

    if args.csv:
        print("\nAfter creating the tables, import the data:\n")
        for name in CORE_TABLES:
            csv = CSV_DIR / f"{name}.csv"
            marker = "" if csv.exists() else "   # (csv not exported yet)"
            print(f"  catalyst ds:import {csv} --table {name}{marker}")
        print("\n(CSV exports are written by `python -m data_engine.build`.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
