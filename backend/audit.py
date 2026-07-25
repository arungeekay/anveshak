"""Audit log writer (contracts.md §8). Every chat/investigate/export/role-switch
writes one row to AuditLog (DuckDB; also NoSQL once Catalyst auth lands at T21)."""
from __future__ import annotations

import datetime as _dt
import json
import threading

# The audit_id is assigned as MAX(audit_id)+1 (read-modify-write). Two concurrent
# writers could compute the same id -> PK violation and a dropped row. Serialize the
# whole operation in-process so ids stay unique (single AppSail worker/instance).
_write_lock = threading.Lock()


def write_audit(con, user_id: str, role: str, action: str, detail: dict) -> int:
    """Best-effort audit write. Never let an audit failure (e.g. a read-only mirror)
    break the request — the Data Store/NoSQL audit is the durable record (ADR-1/§8)."""
    try:
        with _write_lock:
            next_id = con.execute(
                "SELECT COALESCE(MAX(audit_id), 0) + 1 FROM AuditLog").fetchone()[0]
            con.execute(
                "INSERT INTO AuditLog (audit_id, ts, user_id, role, action, detail) "
                "VALUES (?,?,?,?,?,?)",
                [int(next_id), _dt.datetime.now(), user_id, role, action,
                 json.dumps(detail, default=str)],
            )
        return int(next_id)
    except Exception:  # noqa: BLE001
        return 0
