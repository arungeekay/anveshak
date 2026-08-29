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
        # Audit rows are hash-chained (F-12); the shipped mirror predates
        # those columns, so add them before anything writes.
        from .audit import ensure_chain_columns
        ensure_chain_columns(con)
        # MO embedding matrix first: linkage, similar_cases and the agent pipeline
        # all read it, and loading it once here keeps every later call sub-second.
        from .embeddings import matrix as embed_matrix
        embed_matrix.ensure(con)
        log.info("prewarm: embedding matrix %d vectors", embed_matrix.size())
        from .linkage.store import store as series_store
        series_store.ensure(con)
        log.info("prewarm: linkage discovered %d series", len(series_store.all(con)))
        from .graph import engine
        engine.cache.ensure(con)
        log.info("prewarm: graph built %d nodes", engine.cache.g.number_of_nodes())
        from .patrol.store import leads_store
        leads_store.ensure(con)
        log.info("prewarm: patrol produced %d leads", len(leads_store.all()))
        # Warm the primary demo series' Investigation Pack so "Open pack" is instant
        # even if a viewer navigates straight to the pack URL without streaming first.
        # This runs the 6-agent pipeline (LLM-dependent); it's the last, fully optional
        # warm step — a failure here never affects anything else.
        demo_series = os.getenv("PREWARM_PACK_SERIES", "SH-07")
        if demo_series:
            try:
                from .api.investigate import _build_pack
                _build_pack(con, demo_series)
                log.info("prewarm: investigation pack ready for %s", demo_series)
            except Exception as exc:  # noqa: BLE001
                log.warning("prewarm pack (%s) skipped: %s", demo_series, exc)
    except Exception as exc:  # noqa: BLE001 - never let warming crash the server
        log.warning("prewarm failed (endpoints will compute lazily): %s", exc)


def _usable(path: str) -> tuple[bool, str]:
    """Can DuckDB open this file and does it hold the corpus?"""
    try:
        import duckdb
        con = duckdb.connect(path, read_only=True)
        try:
            n = con.execute("SELECT COUNT(*) FROM CaseMaster").fetchone()[0]
        finally:
            con.close()
        return (n > 0), f"{n} cases"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:140]


def _prepare_database(src: str) -> None:
    """Put a WRITABLE, VALIDATED database in place before the app serves anything.

    AppSail's /app is read-only, so the mirror is copied to /tmp — the audit log and
    FIR intake both need to write. Three lessons are baked in here:

    * the copy is UNCONDITIONAL. It used to be skipped when /tmp already held a
      file, so a corrupt copy from an earlier bad image survived every redeploy.
    * both the source and the copy are validated. A torn database (an image built
      while something held the file open) otherwise shows up only as every endpoint
      500ing, with nothing in the logs pointing at the cause.
    * if the copy is unusable we fall back to the bundled read-only path rather than
      serving from a file we know is broken.
    """
    ok, detail = _usable(src)
    if not ok:
        log.error("BUNDLED DATABASE IS UNUSABLE (%s). The image was probably built "
                  "from a mid-write copy — rebuild with scripts/stage_db.py.", detail)
        return
    log.info("bundled database ok: %s", detail)

    dst = "/tmp/anveshak.duckdb"
    try:
        for stale in (dst, dst + ".wal"):
            if os.path.exists(stale):
                os.remove(stale)
        shutil.copy(src, dst)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not stage a writable database (%s); using the bundled "
                    "read-only copy", exc)
        return

    ok, detail = _usable(dst)
    if ok:
        os.environ["DUCKDB_PATH"] = dst
        log.info("writable database ready at %s (%s)", dst, detail)
    else:
        log.error("copy at %s is unusable (%s); falling back to %s", dst, detail, src)


def main() -> None:
    port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))
    # AppSail's /app is read-only; the DuckDB mirror needs a WRITABLE location so the
    # audit log (and any write) works. Copy the bundled DB to /tmp and repoint.
    src = os.getenv("DUCKDB_PATH", "build/anveshak.duckdb")
    if os.path.exists(src):
        _prepare_database(src)
    # Kick off cache warming so the container is demo-ready shortly after boot; the
    # server starts serving immediately (health/root respond while warming runs).
    threading.Thread(target=_prewarm, name="prewarm", daemon=True).start()
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
