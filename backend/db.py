"""DuckDB access for the analytical mirror (ADR-1).

The DuckDB file is built by data_engine and, in production, rebuilt from the
Catalyst Data Store on AppSail startup. Runtime queries (NL->SQL, tools) run here.
"""
from __future__ import annotations

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
