"""AppSail entrypoint: read Catalyst's injected listen port and run uvicorn.

Using a Python launcher (rather than `uvicorn ... --port $X_ZOHO_CATALYST_LISTEN_PORT`
in the command string) avoids any shell env-var expansion ambiguity in the managed
runtime — the port is read programmatically.
"""
from __future__ import annotations

import logging
import os
import shutil
import threading

import uvicorn

log = logging.getLogger("anveshak.serve")


def _prewarm() -> None:
    """Warm the expensive caches (linkage discovery, CrimeGraph, Night-Patrol
    detectors) in a background thread at startup. Each cold computation takes tens of
    seconds — longer than the AppSail gateway's request timeout — so the FIRST demo
    request to /api/series, /api/graph or /api/leads must never trigger it live.
    Runs off the request path; failures are non-fatal (endpoints fall back to lazy,
    stampede-locked computation)."""
    try:
        from .db import get_connection
        con = get_connection()
        from .linkage.store import store as series_store
        series_store.ensure(con)
        log.info("prewarm: linkage discovered %d series", len(series_store.all(con)))
        from .graph import engine
        engine.cache.ensure(con)
        log.info("prewarm: graph built %d nodes", engine.cache.g.number_of_nodes())
        from .patrol.store import leads_store
        leads_store.ensure(con)
        log.info("prewarm: patrol produced %d leads", len(leads_store.all()))
    except Exception as exc:  # noqa: BLE001 - never let warming crash the server
        log.warning("prewarm failed (endpoints will compute lazily): %s", exc)


def main() -> None:
    port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))
    # AppSail's /app is read-only; the DuckDB mirror needs a WRITABLE location so the
    # audit log (and any write) works. Copy the bundled DB to /tmp and repoint.
    src = os.getenv("DUCKDB_PATH", "build/anveshak.duckdb")
    if os.path.exists(src):
        dst = "/tmp/anveshak.duckdb"
        try:
            if not os.path.exists(dst):
                shutil.copy(src, dst)
            os.environ["DUCKDB_PATH"] = dst
        except Exception:  # noqa: BLE001 - fall back to the read-only bundled path
            pass
    # Kick off cache warming so the container is demo-ready shortly after boot; the
    # server starts serving immediately (health/root respond while warming runs).
    threading.Thread(target=_prewarm, name="prewarm", daemon=True).start()
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
