"""Audit read endpoint (contracts.md §8). SCRB-only RBAC lands with auth at T21."""
from __future__ import annotations

from fastapi import APIRouter

from ..db import get_connection

router = APIRouter()


@router.get("/api/audit")
def audit(limit: int = 100) -> list[dict]:
    rows = get_connection().execute(
        "SELECT ts, user_id, role, action, detail FROM AuditLog ORDER BY audit_id DESC LIMIT ?",
        [limit],
    ).fetchall()
    return [{"ts": str(r[0]), "user_id": r[1], "role": r[2], "action": r[3], "detail": r[4]}
            for r in rows]
