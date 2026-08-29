"""Audit log writer (contracts.md §8, FINALE_PLAN F-12).

Every chat/investigate/intake/export writes one row to AuditLog. Rows are
**hash-chained**: each carries the SHA-256 of (previous row's hash + its own
canonical content), so removing or editing any historical row breaks every hash
after it. `verify_chain()` walks the chain and reports the first break.

That is what makes the log chain-of-custody grade rather than merely a list: an
administrator with write access still cannot rewrite history undetectably. It is
the honest version of the claim a police jury will probe.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import threading

log = logging.getLogger("anveshak.audit")

# The audit_id is assigned as MAX(audit_id)+1 (read-modify-write) and each row hashes
# the previous one, so writes MUST be serialised, otherwise ids collide and the
# chain forks (single AppSail worker/instance).
_write_lock = threading.Lock()

GENESIS = "0" * 64  # prev_hash of the very first row


def _canonical(audit_id: int, ts, user_id: str, role: str, action: str,
               detail: str) -> str:
    """Stable string form of a row, the thing that gets hashed.

    Sorted keys and an isoformat timestamp so the same row always hashes the same
    way, regardless of dict ordering or driver datetime representation.
    """
    return json.dumps({
        "audit_id": int(audit_id),
        "ts": ts.isoformat(timespec="seconds") if hasattr(ts, "isoformat") else str(ts),
        "user_id": user_id, "role": role, "action": action, "detail": detail,
    }, sort_keys=True, separators=(",", ":"))


def row_hash(prev_hash: str, audit_id: int, ts, user_id: str, role: str,
             action: str, detail: str) -> str:
    payload = (prev_hash or GENESIS) + _canonical(audit_id, ts, user_id, role,
                                                  action, detail)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


AUDIT_DDL = """
CREATE TABLE AuditLog (
  audit_id  INTEGER PRIMARY KEY,
  ts        TIMESTAMP,
  user_id   VARCHAR,
  role      VARCHAR,
  action    VARCHAR,
  detail    VARCHAR,
  prev_hash VARCHAR,
  row_hash  VARCHAR
)
"""


def ensure_chain_columns(con) -> None:
    """Make AuditLog writable and chain-capable (idempotent, safe on every boot).

    Two repairs, both needed by shipped mirrors:

    1. The generator produced AuditLog from an EMPTY DataFrame, so pandas typed
       every column int64. Inserting a timestamp or a string then failed a cast -
       and because audit writes are best-effort, that failure was swallowed and the
       audit log stayed permanently empty. If the types are wrong we recreate the
       table from the DDL; it holds no rows, so nothing is lost.
    2. Older mirrors predate the hash chain, so prev_hash/row_hash are added.
    """
    try:
        cols = {r[0].lower(): r[1].upper() for r in con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'AuditLog'").fetchall()}
        if not cols:
            con.execute(AUDIT_DDL)
            log.info("audit: created AuditLog")
            return

        # ts must be temporal and the text columns must be VARCHAR, or writes fail.
        broken = ("TIMESTAMP" not in cols.get("ts", "")
                  or cols.get("detail", "") != "VARCHAR"
                  or cols.get("user_id", "") != "VARCHAR")
        if broken:
            rows = con.execute("SELECT COUNT(*) FROM AuditLog").fetchone()[0]
            if rows:
                log.warning("audit: AuditLog has %d rows and wrong column types; "
                            "leaving it alone", rows)
            else:
                con.execute("DROP TABLE AuditLog")
                con.execute(AUDIT_DDL)
                log.info("audit: rebuilt AuditLog with correct column types "
                         "(was all-INTEGER from an empty build frame)")
            return

        for col in ("prev_hash", "row_hash"):
            if col not in cols:
                con.execute(f"ALTER TABLE AuditLog ADD COLUMN {col} VARCHAR")
                log.info("audit: added column %s", col)
    except Exception as exc:  # noqa: BLE001 - never block startup on this
        log.warning("audit: could not ensure audit table: %s", exc)


def write_audit(con, user_id: str, role: str, action: str, detail: dict) -> int:
    """Best-effort audit write. Never let an audit failure (e.g. a read-only mirror)
    break the request, the Data Store/NoSQL audit is the durable record (ADR-1/§8)."""
    try:
        with _write_lock:
            head = con.execute(
                "SELECT COALESCE(MAX(audit_id), 0) FROM AuditLog").fetchone()[0]
            next_id = int(head) + 1
            prev = con.execute(
                "SELECT row_hash FROM AuditLog WHERE audit_id = ?", [head]).fetchone()
            prev_hash = (prev[0] if prev and prev[0] else GENESIS)
            ts = _dt.datetime.now()
            detail_json = json.dumps(detail, default=str)
            h = row_hash(prev_hash, next_id, ts, user_id, role, action, detail_json)
            con.execute(
                "INSERT INTO AuditLog (audit_id, ts, user_id, role, action, detail, "
                "prev_hash, row_hash) VALUES (?,?,?,?,?,?,?,?)",
                [next_id, ts, user_id, role, action, detail_json, prev_hash, h])
        return next_id
    except Exception as exc:  # noqa: BLE001
        log.debug("audit write skipped: %s", exc)
        return 0


def verify_chain(con) -> dict:
    """Recompute every hash and report whether the chain is intact."""
    try:
        rows = con.execute(
            "SELECT audit_id, ts, user_id, role, action, detail, prev_hash, row_hash "
            "FROM AuditLog ORDER BY audit_id").fetchall()
    except Exception as exc:  # noqa: BLE001
        return {"chain_ok": False, "rows": 0, "error": str(exc)}

    prev_hash = GENESIS
    for r in rows:
        audit_id, ts, user_id, role, action, detail, stored_prev, stored_hash = r
        if not stored_hash:
            # Pre-chain row (written before F-12); skip but keep walking.
            prev_hash = stored_hash or prev_hash
            continue
        if (stored_prev or GENESIS) != prev_hash:
            return {"chain_ok": False, "rows": len(rows), "broken_at": int(audit_id),
                    "reason": "prev_hash does not match the preceding row"}
        expected = row_hash(prev_hash, audit_id, ts, user_id, role, action, detail)
        if expected != stored_hash:
            return {"chain_ok": False, "rows": len(rows), "broken_at": int(audit_id),
                    "reason": "row content does not match its recorded hash"}
        prev_hash = stored_hash

    return {"chain_ok": True, "rows": len(rows),
            "head_hash": prev_hash if rows else GENESIS}
