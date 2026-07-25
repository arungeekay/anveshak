"""AppSail entrypoint: read Catalyst's injected listen port and run uvicorn.

Using a Python launcher (rather than `uvicorn ... --port $X_ZOHO_CATALYST_LISTEN_PORT`
in the command string) avoids any shell env-var expansion ambiguity in the managed
runtime — the port is read programmatically.
"""
from __future__ import annotations

import os
import shutil

import uvicorn


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
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
