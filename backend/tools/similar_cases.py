"""similar_cases tool (contracts.md §7): cosine over precomputed CaseMOVector."""
from __future__ import annotations

import numpy as np

from ..db import get_connection


def similar_cases(case_id: int, k: int = 5, con=None) -> list[dict]:
    con = con or get_connection()
    row = con.execute("SELECT embedding FROM CaseMOVector WHERE CaseMasterID = ?", [case_id]).fetchone()
    if not row or row[0] is None:
        return []
    q = np.asarray(row[0], dtype=float)
    q /= np.linalg.norm(q) + 1e-9
    rows = con.execute(
        "SELECT CaseMasterID, embedding FROM CaseMOVector WHERE CaseMasterID <> ?", [case_id]
    ).fetchall()
    ids = np.array([r[0] for r in rows])
    mat = np.asarray([r[1] for r in rows], dtype=float)
    mat /= (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
    sims = mat @ q
    top = np.argsort(-sims)[:k]
    out = []
    for i in top:
        cid = int(ids[i])
        brief = con.execute("SELECT BriefFacts FROM CaseMaster WHERE CaseMasterID = ?", [cid]).fetchone()
        out.append({"case_id": cid, "similarity": round(float(sims[i]), 3),
                    "summary": (brief[0] or "")[:160] if brief else ""})
    return out
