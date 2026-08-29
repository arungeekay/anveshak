#!/usr/bin/env python
"""Restore pristine demo state (contracts/demo_path).

Default (fast, <60s): refresh the runtime caches on a running server -
re-discover series, rebuild the graph, re-run Night Patrol detectors.
--rebuild also regenerates build/anveshak.duckdb from the seed (slower; embeds).

Usage:
  python scripts/demo_reset.py [--url http://localhost:8000] [--rebuild]
"""
from __future__ import annotations

import argparse
import time
import urllib.request


def _post(url: str) -> dict:
    req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:  # noqa: S310 (local demo)
        import json
        return json.loads(r.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    if args.rebuild:
        from data_engine.build import build_dataset
        print("Rebuilding build/anveshak.duckdb …")
        build_dataset()

    print("Rescanning series …", _post(f"{args.url}/api/series/rescan").get("count"))
    print("Rebuilding graph …", _post(f"{args.url}/api/graph/rebuild").get("nodes"))
    print("Running Night Patrol …", _post(f"{args.url}/api/leads/run").get("count"))
    print(f"Demo reset complete in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
