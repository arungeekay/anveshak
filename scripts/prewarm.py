#!/usr/bin/env python
"""Pre-warm caches after a deploy by hitting the golden-path endpoints.

Usage: python scripts/prewarm.py [--url http://localhost:8000]
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request


def _get(url: str):
    with urllib.request.urlopen(url, timeout=180) as r:  # noqa: S310
        return json.loads(r.read())


def _post(url: str, body: dict):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:  # noqa: S310
        return json.loads(r.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    args = ap.parse_args()
    u = args.url
    t0 = time.time()
    print("health:", _get(f"{u}/api/health"))
    print("series:", len(_get(f"{u}/api/series")), "discovered")
    print("graph:", _post(f"{u}/api/graph/query",
                          {"type": "ego_network", "params": {"person_key": "P-007001", "depth": 1}})
          ["nodes"].__len__(), "nodes")
    print("leads:", _post(f"{u}/api/leads/run", {}).get("count"))
    print(f"prewarm complete in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
