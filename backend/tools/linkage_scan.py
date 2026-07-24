"""linkage_scan tool (contracts.md §7): full rescan or series containing a case."""
from __future__ import annotations

from ..db import get_connection
from ..linkage.store import store


def linkage_scan(case_id: int | None = None, con=None) -> list[dict]:
    con = con or get_connection()
    if case_id is None:
        return store.all(con)
    return store.containing(con, int(case_id))
