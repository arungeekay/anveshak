"""Build the DuckDB analytical mirror from generated tables (ADR-1).

`build_duckdb` loads a tables dict into DuckDB and creates the analyst views from
schema/schema.sql. Used in-memory by eval/test_planted.py and to write the on-disk
build/anveshak.duckdb (T05 adds MO-vector embeddings + CSV export on top).
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import duckdb
import pandas as pd

from . import mo
from .generator import generate

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "schema.sql"
DEFAULT_DB = REPO_ROOT / "build" / "anveshak.duckdb"


def _coerce_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Convert object columns holding python date/datetime to datetime64 so DuckDB
    infers temporal types (year()/date_trunc work reliably)."""
    for col in df.columns:
        if df[col].dtype == object and len(df):
            sample = df[col].dropna()
            if len(sample) and isinstance(sample.iloc[0], _dt.date):  # datetime subclasses date
                df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_tables_into(con: duckdb.DuckDBPyConnection, tables: dict[str, pd.DataFrame]) -> None:
    for name, df in tables.items():
        if name.startswith("_"):
            continue
        frame = _coerce_dates(df.copy())
        con.register("_df", frame)
        con.execute(f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM _df')
        con.unregister("_df")


def create_views(con: duckdb.DuckDBPyConnection) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    for stmt in sql.split(";"):
        # Drop leading -- comment lines so the CREATE VIEW is at the start.
        lines = [ln for ln in stmt.splitlines() if not ln.strip().startswith("--")]
        s = "\n".join(lines).strip()
        if s.upper().startswith("CREATE VIEW"):
            con.execute(s.replace("CREATE VIEW", "CREATE OR REPLACE VIEW", 1))


def build_duckdb(tables: dict[str, pd.DataFrame], path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(path)
    load_tables_into(con, tables)
    create_views(con)
    return con


def compute_mo_vectors(tables: dict[str, pd.DataFrame]) -> None:
    """Precompute CaseMOVector (embedding + structured MO features) for all cases."""
    cm = tables["CaseMaster"]
    briefs = cm["BriefFacts"].fillna("").tolist()
    feats = [mo.features_json(r.BriefFacts, r.IncidentFromDate, r.latitude, r.longitude)
             for r in cm.itertuples(index=False)]
    embs = mo.embed_texts(briefs)
    tables["CaseMOVector"] = pd.DataFrame({
        "CaseMasterID": cm["CaseMasterID"].astype(int).tolist(),
        "embedding": [e.astype(float).tolist() for e in embs],
        "mo_features": feats,
        "model": mo.EMBED_MODEL,
    })


def export_csvs(tables: dict[str, pd.DataFrame], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        if name.startswith("_"):
            continue
        df.to_csv(out_dir / f"{name}.csv", index=False)


def build_dataset(seed: int = 42, n_cases: int = 15000, out_path: Path | None = DEFAULT_DB,
                  embeddings: bool = True, export_csv: bool = True):
    """Full build: generate planted dataset, embed, write DuckDB + CSVs, return (con, truth)."""
    tables, truth = generate(seed=seed, n_cases=n_cases, plant=True, return_truth=True)
    if embeddings:
        compute_mo_vectors(tables)
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.unlink(missing_ok=True)
        con = build_duckdb(tables, str(out_path))
        (out_path.parent / "planted_truth.json").write_text(json.dumps(truth, indent=2, default=str),
                                                             encoding="utf-8")
        if export_csv:
            export_csvs(tables, out_path.parent / "csv")
    else:
        con = build_duckdb(tables)
    return con, truth


def main() -> None:
    con, truth = build_dataset()
    n_cases = con.execute("SELECT COUNT(*) FROM vw_case_360").fetchone()[0]
    n_vec = con.execute("SELECT COUNT(*) FROM CaseMOVector").fetchone()[0]
    d1 = con.execute("""SELECT COUNT(*) FROM vw_case_360
        WHERE crime_sub_head='Chain Snatching' AND district='Bengaluru City'
          AND year(CrimeRegisteredDate)=2026""").fetchone()[0]
    print(f"cases (vw_case_360): {n_cases}")
    print(f"CaseMOVector rows : {n_vec}")
    print(f"D1 scalar (Chain Snatching, Bengaluru City, 2026): {d1}")
    print(f"SH-07 series_id   : {truth['SP1']['series_id']}")
    print(f"DB written to     : {DEFAULT_DB}")


if __name__ == "__main__":
    main()
