"""Build the DuckDB analytical mirror from generated tables (ADR-1).

`build_duckdb` loads a tables dict into DuckDB and creates the analyst views from
schema/schema.sql. Used in-memory by eval/test_planted.py and to write the on-disk
build/anveshak.duckdb (T05 adds MO-vector embeddings + CSV export on top).
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "schema.sql"


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
            con.execute(s)


def build_duckdb(tables: dict[str, pd.DataFrame], path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(path)
    load_tables_into(con, tables)
    create_views(con)
    return con
