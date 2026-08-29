"""Catalyst Data Store integration (ADR-1, FINALE_PLAN F-07).

ADR-1 says the Data Store is the system of record and DuckDB is a fast analytical
mirror. This module makes that literal rather than aspirational: it reports the
live Data Store row counts and writes new FIRs there as well as to the mirror.

Two honest constraints, both surfaced in the status payload rather than hidden:

* Data Store tables and their column types are defined in the Catalyst **console**
  (see docs/catalyst/datastore.md), so a deployment where they have not been
  created reports `mode: "bundled-mirror"` — never a fabricated "connected".
* The SDK authorises from the *incoming request's* Catalyst headers, which is why
  every function here takes the current request context.

`scripts/datastore_schema.py` prints the exact table/column definitions to create.
"""
from __future__ import annotations

import logging

from .llm.request_ctx import current_request

log = logging.getLogger("anveshak.datastore")

# The core tables mirrored into the Data Store. CaseMaster is the one that matters
# for the "system of record" claim; the rest are reference data.
CORE_TABLES = ("CaseMaster", "District", "PersonRegistry", "AuditLog")


class DataStoreUnavailable(RuntimeError):
    """The Data Store cannot be reached from this context."""


def _app():
    """Initialise the Catalyst SDK from the current request's headers."""
    req = current_request.get()
    if req is None:
        raise DataStoreUnavailable("no request context")
    try:
        import zcatalyst_sdk
    except ImportError as exc:  # pragma: no cover
        raise DataStoreUnavailable("zcatalyst_sdk not installed") from exc

    class _HeaderReq:
        def __init__(self, raw_headers):
            self.headers = {k.decode("latin-1"): v.decode("latin-1")
                            for k, v in raw_headers}

    try:
        return zcatalyst_sdk.initialize(req=_HeaderReq(req.headers.raw))
    except Exception as exc:  # noqa: BLE001
        raise DataStoreUnavailable(f"SDK init failed: {exc}") from exc


def status() -> dict:
    """Live Data Store connectivity + row counts, or an honest 'not wired' answer."""
    try:
        app = _app()
        app.datastore()  # probe: raises if the Data Store is not reachable
    except DataStoreUnavailable as exc:
        return {"connected": False, "mode": "bundled-mirror", "detail": str(exc),
                "note": "DuckDB mirror is serving all reads; Data Store tables are "
                        "created in the Catalyst console (see docs/catalyst/datastore.md)"}

    counts, errors = {}, {}
    for name in CORE_TABLES:
        try:
            zcql = app.zcql()
            rows = zcql.execute_query(f"SELECT COUNT(ROWID) FROM {name}")
            first = rows[0][name] if rows else {}
            counts[name] = int(next(iter(first.values()))) if first else 0
        except Exception as exc:  # noqa: BLE001 - report per table, don't abort
            errors[name] = str(exc)[:120]

    connected = bool(counts)
    return {
        "connected": connected,
        "mode": "datastore" if connected else "bundled-mirror",
        "row_counts": counts,
        "errors": errors or None,
        "note": ("Data Store is the system of record; DuckDB mirrors it for "
                 "sub-second analytics (ADR-1)." if connected else
                 "Data Store tables not found — create them in the console."),
    }


def insert_case(row: dict) -> bool:
    """Write a newly registered FIR to the Data Store (best-effort).

    Returns True only on a real write, so callers can report accurately. Failure is
    never fatal: the DuckDB mirror already holds the case and the demo continues.
    """
    try:
        app = _app()
        table = app.datastore().table("CaseMaster")
        table.insert_row({k: (str(v) if v is not None else None)
                          for k, v in row.items()})
        return True
    except Exception as exc:  # noqa: BLE001
        log.info("data store write skipped: %s", exc)
        return False
