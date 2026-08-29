"""DuckDB access for the analytical mirror (ADR-1).

The DuckDB file is built by data_engine and, in production, rebuilt from the
Catalyst Data Store on AppSail startup. Runtime queries (NL->SQL, tools) run here.
"""
from __future__ import annotations

import datetime as _dt
import threading
from pathlib import Path

import duckdb

from .config import settings

_lock = threading.Lock()
_conn: duckdb.DuckDBPyConnection | None = None
_generation = 0
_local = threading.local()


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return a **per-thread** DuckDB cursor over the process-wide database.

    A single ``DuckDBPyConnection`` is NOT thread-safe: FastAPI runs sync endpoints
    in a threadpool, so concurrent requests sharing one connection race and return
    corrupt/empty results. The documented fix is one cursor per thread (each cursor
    is an independent execution context over the same shared database), which is what
    we hand back here. If the DB file does not exist yet, an in-memory connection is
    used so the app still boots (health reports db: not_loaded).
    """
    global _conn, _generation
    with _lock:
        if _conn is None:
            path = Path(settings.duckdb_path)
            if path.exists():
                _conn = duckdb.connect(str(path), read_only=False)
            else:
                _conn = duckdb.connect(":memory:")
            _generation += 1
        gen = _generation
        cur = getattr(_local, "cursor", None)
        if cur is None or getattr(_local, "gen", None) != gen:
            # Create the per-thread cursor under the lock so it can't race with a
            # concurrent reset/re-open of the base connection.
            cur = _conn.cursor()
            _local.cursor = cur
            _local.gen = gen
        return cur


_data_max_date: _dt.date | None = None


def data_max_date(con=None) -> _dt.date:
    """The dataset's most recent FIR date — the anchor for every relative window.

    Detectors ("last 14 days"), recency scoring and demo narratives must measure
    from the data's own end, never from the wall clock: the corpus ends 2026-07-20,
    so a wall-clock anchor would find an empty window at any later demo date
    (FINALE_PLAN F-02). Derived from the data rather than hardcoded so that FIR
    intake (F-06) extending the corpus shifts the anchor automatically.

    Cached; call reset_connection() (or reset_data_max_date()) after inserts.
    """
    global _data_max_date
    if _data_max_date is None:
        con = con or get_connection()
        row = con.execute("SELECT MAX(CrimeRegisteredDate) FROM CaseMaster").fetchone()
        val = row[0] if row else None
        # DuckDB may hand back a datetime; normalise to date. Duck-typed rather than
        # isinstance() so a monkeypatched datetime class (tests) still converts.
        if val is not None and hasattr(val, "date") and callable(val.date):
            val = val.date()
        _data_max_date = val or _dt.date(2026, 7, 20)  # fallback: known corpus end
    return _data_max_date


def reset_data_max_date() -> None:
    """Forget the cached anchor (after intake inserts a newer case)."""
    global _data_max_date
    _data_max_date = None


def db_status() -> dict:
    """Health probe: is the mirror loaded, and how many cases?"""
    path = Path(settings.duckdb_path)
    if not path.exists():
        return {"db": "not_loaded", "cases": 0}
    try:
        conn = get_connection()
        exists = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'CaseMaster'"
        ).fetchone()[0]
        if not exists:
            return {"db": "not_loaded", "cases": 0}
        cases = conn.execute("SELECT COUNT(*) FROM CaseMaster").fetchone()[0]
        return {"db": "loaded", "cases": int(cases)}
    except Exception as exc:  # pragma: no cover - defensive
        return {"db": "error", "cases": 0, "detail": str(exc)}


def reset_connection() -> None:
    """Drop the cached connection (used after a mirror rebuild / in tests)."""
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None
