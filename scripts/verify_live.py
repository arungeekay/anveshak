"""verify_live.py, post-deploy gate for the deployed ANVESHAK app (FINALE_PLAN F-04).

Asserts the golden path against the LIVE deployment and exits non-zero on any
failure, so it can gate every deploy in the finale build.

    python scripts/verify_live.py                 # default prod base URL
    python scripts/verify_live.py --base http://localhost:8000
    python scripts/verify_live.py --warm          # pre-warm first (cold container)
    python scripts/verify_live.py --skip-slow     # skip concurrency + investigation

Cold containers take 60-90s to prewarm; --warm polls until the heavy endpoints are
cached before the checks run (see FINALE_PLAN.md 0.2).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

DEFAULT_BASE = "https://anveshak-api-50044329134.development.catalystappsail.in"
EXPECTED_CASES = 15405
D1_QUESTION = "How many chain snatching cases were registered in Bengaluru City in 2026?"
D1_ANSWER_CONTAINS = "47"
KN_QUESTION = "ಈ ವರ್ಷ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಎಷ್ಟು ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ?"
PRAKASH_KEY = "P-007001"

results: list[tuple[str, bool, str]] = []


def _req(url: str, *, payload: dict | None = None, timeout: int = 120,
         headers: dict | None = None) -> tuple[int, bytes]:
    data = json.dumps(payload).encode() if payload is not None else None
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=hdrs,
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def get_json(base: str, path: str, *, payload: dict | None = None,
             timeout: int = 120, headers: dict | None = None):
    status, body = _req(base + path, payload=payload, timeout=timeout, headers=headers)
    if status != 200:
        raise AssertionError(f"{path} -> HTTP {status}")
    if not body:
        raise AssertionError(f"{path} -> empty body")
    return json.loads(body)


def check(name: str, fn) -> bool:
    """Run one check; record pass/fail with timing. Never raises."""
    t0 = time.time()
    try:
        detail = fn() or "ok"
        results.append((name, True, f"{detail}  [{time.time() - t0:.1f}s]"))
        return True
    except Exception as exc:  # noqa: BLE001 - report every failure uniformly
        results.append((name, False, f"{type(exc).__name__}: {exc}  [{time.time() - t0:.1f}s]"))
        return False


def warm(base: str, tries: int = 25) -> None:
    """Poll the heavy endpoints until the container's caches are warm."""
    print("warming…", end="", flush=True)
    for i in range(tries):
        try:
            t0 = time.time()
            get_json(base, "/api/series", timeout=120)
            get_json(base, "/api/leads", timeout=120)
            if time.time() - t0 < 3.0:
                print(f" warm after {i + 1} probe(s)")
                return
        except Exception:  # noqa: BLE001 - cold container may 408/500 while starting
            pass
        print(".", end="", flush=True)
        time.sleep(6)
    print(" (still slow, continuing anyway)")


# --- individual checks -------------------------------------------------------

def c_health(base):
    d = get_json(base, "/api/health", timeout=90)
    assert d["status"] == "ok", d
    assert d["db"] == "loaded", d
    assert d["cases"] == EXPECTED_CASES, f"cases={d['cases']} expected {EXPECTED_CASES}"
    return f"db loaded, {d['cases']} cases, llm={d['llm_backend']}"


def c_spa(base):
    status, body = _req(base + "/ui/", timeout=60)
    assert status == 200, f"HTTP {status}"
    assert b"<div id=\"root\"" in body or b"<html" in body.lower(), "not an HTML shell"
    return "SPA served"


def c_chat_en(base):
    d = get_json(base, "/api/chat", payload={"message": D1_QUESTION, "lang": "en"})
    ans = d.get("answer_text") or ""
    assert D1_ANSWER_CONTAINS in ans, f"answer lacks {D1_ANSWER_CONTAINS!r}: {ans!r}"
    ev = d.get("evidence") or {}
    assert ev.get("sql"), "no SQL in evidence drawer"
    return f"{ans[:58]}… (tool={ev.get('tool')})"


def c_chat_kn(base):
    d = get_json(base, "/api/chat", payload={"message": KN_QUESTION, "lang": "kn"})
    ans = (d.get("answer_text") or "").strip()
    assert ans, "empty Kannada answer"
    assert any("ಀ" <= ch <= "೿" for ch in ans), f"no Kannada script: {ans!r}"
    return ans[:40]


def c_series(base):
    d = get_json(base, "/api/series")
    sh07 = next((s for s in d if s["series_id"] == "SH-07"), None)
    assert sh07, "SH-07 not discovered"
    assert sh07["confidence"] >= 0.85, f"confidence {sh07['confidence']} < 0.85"
    assert len(sh07["case_ids"]) == 15, f"{len(sh07['case_ids'])} cases, expected 15"
    assert len(sh07["districts"]) >= 3, f"districts {sh07['districts']}"
    return (f"{len(d)} series; SH-07 conf {sh07['confidence']}, "
            f"{len(sh07['case_ids'])} cases, {len(sh07['districts'])} districts")


def c_graph(base):
    d = get_json(base, "/api/graph/query",
                 payload={"type": "ego_network",
                          "params": {"person_key": PRAKASH_KEY, "depth": 1}})
    n = len(d.get("nodes") or [])
    assert n >= 25, f"only {n} nodes for {PRAKASH_KEY}"
    return f"{PRAKASH_KEY} hub: {n} nodes"


def c_leads(base):
    d = get_json(base, "/api/leads")
    types = {x["type"] for x in d}
    assert len(d) >= 3, f"only {len(d)} leads"
    for t in ("spike", "repeat_offender", "series_growth"):
        assert t in types, f"detector {t} did not fire (got {sorted(types)})"
    return f"{len(d)} leads: {sorted(types)}"


def c_pack(base):
    d = get_json(base, "/api/investigate/SH-07/pack")
    pack = d.get("pack")
    assert pack, "pack not cached/assembled"
    assert len(pack.get("suspects_ranked") or []) >= 5, "fewer than 5 ranked suspects"
    assert pack.get("legal"), "no legal section"
    return (f"{len(pack['suspects_ranked'])} suspects, "
            f"{len(pack.get('leads') or [])} leads, forecast="
            f"{(pack.get('forecast') or {}).get('next_window')}")


def c_concurrency(base):
    paths = ["/api/health", "/api/series", "/api/leads", "/api/audit?limit=50"]
    def one(i):
        status, body = _req(base + paths[i % len(paths)], timeout=90)
        return status, len(body)
    with ThreadPoolExecutor(max_workers=20) as ex:
        out = list(ex.map(one, range(20)))
    bad = [(s, n) for s, n in out if s != 200 or n == 0]
    assert not bad, f"{len(bad)}/20 bad responses: {bad[:4]}"
    return "20 concurrent requests: all 200, no empty bodies"


def c_similar_by_text(base):
    """Runtime embedding (F-05/F-06): unseen wording must retrieve the right MO."""
    narrative = ("Two men on a black motorbike rode up behind a woman walking alone "
                 "and the pillion rider snatched her gold chain before speeding off.")
    d = get_json(base, "/api/similar/by_text",
                 payload={"narrative": narrative, "k": 5})
    matches = d.get("matches") or []
    assert len(matches) >= 3, f"only {len(matches)} matches"
    assert matches[0]["cosine"] > 0.6, f"weak top match {matches[0]['cosine']}"
    subs = [m["crime_sub_head"] for m in matches]
    assert subs.count("Chain Snatching") >= 2, f"MO not recognised: {subs}"
    return f"top cosine {matches[0]['cosine']}, {subs.count('Chain Snatching')}/5 chain snatching"


def c_intake_roundtrip(base):
    """The flagship beat: a paraphrased FIR joins SH-07, then state is restored."""
    narrative = ("Yesterday evening my mother was walking by herself near the market "
                 "when two men on a black motorbike came from behind, the pillion "
                 "rider grabbed her gold chain and they sped away against the "
                 "one-way traffic with helmet visors down.")
    d = get_json(base, "/api/intake",
                 payload={"narrative": narrative, "district": "Bengaluru City",
                          "police_station": "Jayanagar PS"}, timeout=120)
    try:
        assert d.get("embedded"), "narrative was not embedded"
        assert "SH-07" in (d.get("joined_series") or []), \
            f"did not join SH-07: {d.get('joined_series')}"
        joined = next(s for s in d["series"] if s["series_id"] == "SH-07")
        detail = (f"case {d['case_id']} joined SH-07 "
                  f"({joined['case_count']} cases, {d['rescan_ms']}ms rescan)")
    finally:
        # Always restore the pristine corpus, even if the assertions failed.
        r = get_json(base, "/api/intake/reset", payload={}, timeout=120)
        assert r["cases"] == EXPECTED_CASES, f"reset left {r['cases']} cases"
    return detail


CHECKS = [
    ("health", c_health, False),
    ("SPA /ui/", c_spa, False),
    ("chat EN (D1)", c_chat_en, False),
    ("chat KN", c_chat_kn, False),
    ("series SH-07", c_series, False),
    ("graph hub", c_graph, False),
    ("leads (3 detectors)", c_leads, False),
    ("investigation pack", c_pack, False),
    ("similar by text", c_similar_by_text, False),
    ("intake -> SH-07", c_intake_roundtrip, True),
    ("concurrency x20", c_concurrency, True),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--warm", action="store_true", help="prewarm before checking")
    ap.add_argument("--skip-slow", action="store_true", help="skip slow checks")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    print(f"verify_live → {base}\n")
    if args.warm:
        warm(base)

    for name, fn, slow in CHECKS:
        if slow and args.skip_slow:
            results.append((name, True, "skipped (--skip-slow)"))
            continue
        check(name, lambda f=fn: f(base))

    width = max(len(n) for n, _, _ in results)
    print()
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {detail}")
    failed = [n for n, ok, _ in results if not ok]
    print()
    if failed:
        print(f"RESULT: {len(failed)} FAILED -> {', '.join(failed)}")
        return 1
    print(f"RESULT: all {len(results)} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
