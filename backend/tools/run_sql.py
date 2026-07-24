"""run_sql tool (contracts.md §7): SELECT-only, guardrailed, auto-limited."""
from __future__ import annotations

from ..db import get_connection
from ..nl2sql import guardrails


def run_sql(sql: str, con=None, *, limit: int = guardrails.DEFAULT_LIMIT) -> dict:
    """Execute a guardrailed read-only query. Returns contract-shaped result."""
    con = con or get_connection()
    safe = guardrails.sanitize(sql, max_limit=limit)
    cur = con.execute(safe)
    columns = [d[0] for d in cur.description]
    rows = [list(r) for r in cur.fetchall()]
    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": len(rows) >= limit,
        "sql": safe,
    }
