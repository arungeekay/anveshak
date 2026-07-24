"""network tool (contracts.md §7): ego network for a person or community for a case."""
from __future__ import annotations

from ..db import get_connection
from ..graph import engine


def network(person_key: str | None = None, case_id: int | None = None,
            depth: int = 2, con=None) -> dict:
    con = con or get_connection()
    if person_key:
        return engine.ego_network(con, person_key, depth)
    if case_id is not None:
        return engine.community_of(con, int(case_id))
    raise ValueError("network requires person_key or case_id")
