"""Stage a verified DuckDB snapshot for the Docker image (post-mortem guard).

**Why this exists.** The Dockerfile used to `COPY build/anveshak.duckdb` directly.
That file is the same one local tests and dev servers write to, so a build started
while anything held it open baked a torn copy into the image, the deployed app
came up with `db: error, cases: 0` and every endpoint 500'd. It is an easy mistake
to repeat and an expensive one to notice, because the build itself succeeds.

So: snapshot to `build/deploy/`, verify the snapshot actually opens and holds the
expected data, and have the Dockerfile copy only from there. A corrupt or
mid-write database now fails the build instead of the demo.

    python scripts/stage_db.py            # snapshot + verify
    python scripts/stage_db.py --clean    # also clear demo residue first
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import duckdb

SRC = Path("build/anveshak.duckdb")
DST = Path("build/deploy/anveshak.duckdb")
EXPECTED_CASES = 15405


def clean(path: Path) -> None:
    """Remove rehearsal residue so the image ships pristine demo state."""
    con = duckdb.connect(str(path))
    try:
        extra = con.execute(
            "SELECT COUNT(*) FROM CaseMaster WHERE CaseMasterID > ?",
            [EXPECTED_CASES]).fetchone()[0]
        if extra:
            con.execute("DELETE FROM CaseMOVector WHERE CaseMasterID > ?",
                        [EXPECTED_CASES])
            con.execute("DELETE FROM CaseMaster WHERE CaseMasterID > ?",
                        [EXPECTED_CASES])
            print(f"  removed {extra} demo-intake case(s)")
        audit = con.execute("SELECT COUNT(*) FROM AuditLog").fetchone()[0]
        if audit:
            con.execute("DELETE FROM AuditLog")
            print(f"  cleared {audit} audit row(s) from testing")
        con.execute("CHECKPOINT")  # flush the WAL into the main file
    finally:
        con.close()


def verify(path: Path) -> bool:
    """Open the snapshot read-only and confirm it holds what the app expects."""
    try:
        con = duckdb.connect(str(path), read_only=True)
    except Exception as exc:  # noqa: BLE001
        print(f"  FAILED to open: {exc}")
        return False
    try:
        cases = con.execute("SELECT COUNT(*) FROM CaseMaster").fetchone()[0]
        vectors = con.execute("SELECT COUNT(*) FROM CaseMOVector").fetchone()[0]
        views = con.execute(
            "SELECT COUNT(*) FROM duckdb_views() WHERE view_name LIKE 'vw_%'"
        ).fetchone()[0]
        audit_ok = con.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name='AuditLog' AND column_name='ts'").fetchone()
        print(f"  cases={cases}  vectors={vectors}  views={views}  "
              f"audit.ts={audit_ok[0] if audit_ok else 'MISSING'}")
        ok = True
        if cases != EXPECTED_CASES:
            print(f"  FAIL: expected {EXPECTED_CASES} cases")
            ok = False
        if vectors != cases:
            print("  FAIL: embedding count does not match case count")
            ok = False
        if views < 4:
            print("  FAIL: analyst views missing")
            ok = False
        if not audit_ok or "TIMESTAMP" not in audit_ok[0].upper():
            # The all-INTEGER AuditLog bug silently disabled every audit write.
            print("  FAIL: AuditLog.ts is not a timestamp column")
            ok = False
        return ok
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true",
                    help="clear demo intake + audit rows before snapshotting")
    args = ap.parse_args()

    if not SRC.exists():
        print(f"{SRC} not found, run `python -m data_engine.build` first")
        return 1

    if args.clean:
        print("cleaning source database…")
        clean(SRC)

    print(f"verifying source {SRC} …")
    if not verify(SRC):
        print("\nSOURCE DATABASE IS NOT USABLE, not staging. "
              "Close anything holding it open and re-run.")
        return 1

    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC, DST)
    wal = SRC.with_suffix(".duckdb.wal")
    if wal.exists():
        print(f"  WARNING: {wal.name} exists, the source was mid-write; "
              f"re-run after closing other processes")
        return 1
    print(f"staged -> {DST} ({DST.stat().st_size / 1e6:.0f} MB)")

    print("verifying the SNAPSHOT (this is what ships) …")
    if not verify(DST):
        print("\nSNAPSHOT IS CORRUPT, the build must not proceed.")
        return 1
    print("\nsnapshot verified; safe to `docker build`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
