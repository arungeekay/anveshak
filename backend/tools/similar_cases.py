"""similar_cases tool (contracts.md §7): cosine over precomputed CaseMOVector.

Vectors come from the process-wide normalised matrix (backend/embeddings/matrix.py)
rather than being re-read and re-normalised from DuckDB on every call, the
Investigation Cell calls this 16x per run (FINALE_PLAN F-03).
"""
from __future__ import annotations

from ..db import get_connection
from ..embeddings import matrix


def similar_cases(case_id: int, k: int = 5, con=None) -> list[dict]:
    con = con or get_connection()
    q = matrix.vector_for(con, case_id)
    if q is None:
        return []
    hits = matrix.search(con, q, k=k, exclude=case_id)
    if not hits:
        return []
    ids = [cid for cid, _ in hits]
    briefs = dict(con.execute(
        "SELECT CaseMasterID, BriefFacts FROM CaseMaster "
        f"WHERE CaseMasterID IN ({','.join(str(i) for i in ids)})"
    ).fetchall())
    return [{"case_id": cid, "similarity": round(sim, 3),
             "summary": (briefs.get(cid) or "")[:160]}
            for cid, sim in hits]
