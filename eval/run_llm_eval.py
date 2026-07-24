"""Run the eval harness with the live NL->SQL engine (Ollama/QuickML) as the solver.

Writes a failure report to eval/failures.md for few-shot tuning (T11).
Usage: python -m eval.run_llm_eval [--db PATH]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from backend.nl2sql import engine
from eval.harness import DEFAULT_DB, load_questions, print_report, run, summarize

FAILURES_MD = Path(__file__).resolve().parent / "failures.md"


def make_solver(con):
    def solve(q: dict) -> str:
        try:
            return engine.run(con, q["question"]).sql
        except Exception:
            return "SELECT 1"  # counts as a miss
    return solve


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args()
    con = duckdb.connect(args.db, read_only=True)
    questions = load_questions()
    results = run(con, make_solver(con), questions)
    summary = summarize(results)
    print_report(summary)

    lines = ["# NL->SQL eval failures (for few-shot tuning)\n"]
    by_id = {q["id"]: q for q in questions}
    for r in results:
        if not r["ok"]:
            q = by_id[r["id"]]
            lines.append(f"## {r['id']} ({r['lang']})\n- Q: {q['question']}\n"
                         f"- gold: {q['gold_sql']}\n- gen:  {r['gen_sql']}\n"
                         f"- err:  {r['error']}\n")
    FAILURES_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {FAILURES_MD}")
    con.close()


if __name__ == "__main__":
    main()
