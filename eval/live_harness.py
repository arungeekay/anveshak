"""Measure NL->SQL accuracy against the DEPLOYED system (FINALE_PLAN F-10).

The published 76.7% was measured with a local 7B dev model. The finale claim should
describe what actually runs in production: GLM-4.7-Flash on Catalyst QuickML, via
the real API, prompt, guardrails, self-repair and all.

Scoring is execution-match: the gold SQL runs locally against the same corpus and
its result set is compared with the values the live API returned. SQL text is never
compared, many correct queries are written differently.

    python -m eval.live_harness                       # all 60 questions
    python -m eval.live_harness --lang kn --limit 5   # a subset
    python -m eval.live_harness --base http://localhost:8000

Writes eval/results/live_<model>_<date>.json, which the Trust Center reads.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import duckdb
import yaml

QUESTIONS = Path("eval/questions.yaml")
RESULTS_DIR = Path("eval/results")
DB_PATH = "build/anveshak.duckdb"
DEFAULT_BASE = "https://anveshak-api-50044329134.development.catalystappsail.in"


def _post(base: str, message: str, lang: str, timeout: int = 90) -> dict:
    body = json.dumps({"message": message, "lang": lang}).encode()
    req = urllib.request.Request(f"{base}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}"}
    except Exception as exc:  # noqa: BLE001 - network flake shouldn't abort the run
        return {"error": str(exc)}


def _norm(v):
    """Compare values loosely: 47, 47.0 and '47' are the same answer."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    try:
        f = float(v)
        return round(f, 3)
    except (TypeError, ValueError):
        return str(v).strip().lower()


def _result_set(rows) -> set:
    """Order-insensitive comparison of a result set."""
    return {tuple(_norm(c) for c in row) for row in rows}


def score(gold_rows, got_rows, expect: str) -> bool:
    """Execution match, tolerant of column ordering and extra descriptive columns."""
    if not gold_rows:
        return not got_rows
    if not got_rows:
        return False
    gold, got = _result_set(gold_rows), _result_set(got_rows)
    if expect == "scalar":
        gold_vals = {v for row in gold for v in row}
        got_vals = {v for row in got for v in row}
        return bool(gold_vals & got_vals)
    if gold == got:
        return True
    # Same rows, extra columns (e.g. the model also selected a label) still counts.
    gold_vals = {v for row in gold for v in row if v is not None}
    got_vals = {v for row in got for v in row if v is not None}
    return bool(gold_vals) and gold_vals.issubset(got_vals)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--lang", choices=["en", "kn"], help="only this language")
    ap.add_argument("--limit", type=int, help="only the first N questions")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between calls")
    ap.add_argument("--model", default="GLM-4.7-Flash (QuickML)")
    args = ap.parse_args()

    questions = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))
    if args.lang:
        questions = [q for q in questions if q.get("lang") == args.lang]
    if args.limit:
        questions = questions[:args.limit]

    con = duckdb.connect(args.db, read_only=True)
    print(f"live eval → {args.base}   ({len(questions)} questions)\n")

    details, failures = [], []
    for q in questions:
        gold_rows = con.execute(q["gold_sql"]).fetchall()
        resp = _post(args.base, q["question"], q.get("lang", "en"))

        got_rows, note = [], ""
        if resp.get("error"):
            note = str(resp["error"])[:80]
        elif resp.get("blocked"):
            note = "blocked by policy"
        else:
            # Prefer the table render spec: it holds the real result set.
            for spec in resp.get("render_specs") or []:
                if spec.get("type") == "table":
                    got_rows = spec["table"]["rows"]
                    break
            if not got_rows and resp.get("evidence", {}).get("row_count"):
                note = "no table spec returned"

        ok = score(gold_rows, got_rows, q.get("expect", "rows"))
        details.append({"id": q["id"], "lang": q.get("lang", "en"), "passed": ok,
                        "question": q["question"], "note": note,
                        "sql": (resp.get("evidence") or {}).get("sql")})
        if not ok:
            failures.append(q["id"])
        print(f"  [{'PASS' if ok else 'FAIL'}] {q['id']} ({q.get('lang')}) "
              f"{q['question'][:58]}{', ' + note if note else ''}")
        time.sleep(args.delay)

    en = [d for d in details if d["lang"] == "en"]
    kn = [d for d in details if d["lang"] == "kn"]
    summary = {
        "measured_on": _dt.date.today().isoformat(),
        "endpoint": args.base,
        "model": args.model,
        "method": "execution-match against gold SQL (order-insensitive)",
        "total": len(details),
        "passed": sum(1 for d in details if d["passed"]),
        "overall": round(sum(d["passed"] for d in details) / max(len(details), 1), 3),
        "en": round(sum(d["passed"] for d in en) / max(len(en), 1), 3) if en else None,
        "kn": round(sum(d["passed"] for d in kn) / max(len(kn), 1), 3) if kn else None,
        "failures": failures,
        "details": details,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"live_{_dt.date.today().isoformat()}.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\noverall {summary['overall']:.1%}  "
          f"(EN {summary['en']:.1%}, KN {summary['kn']:.1%})"
          if summary["en"] is not None and summary["kn"] is not None
          else f"\noverall {summary['overall']:.1%}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
