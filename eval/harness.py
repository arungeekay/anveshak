"""Execution-match eval harness for NL->SQL (contracts.md §9).

Scoring: execute the generated SQL and the gold SQL against the DuckDB mirror and
compare result sets order-insensitively (float tolerance 1e-6). Reports per-language
accuracy and a failure list. A `solver` is any callable question-dict -> SQL string;
the built-in gold_solver returns the gold SQL (sanity: gold vs gold = 100%).
"""
from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

import duckdb
import yaml

QUESTIONS_PATH = Path(__file__).resolve().parent / "questions.yaml"
DEFAULT_DB = Path(__file__).resolve().parent.parent / "build" / "anveshak.duckdb"

Solver = Callable[[dict], str]


def load_questions(path: Path = QUESTIONS_PATH) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _norm_cell(v):
    if isinstance(v, float):
        return round(v, 6)
    if isinstance(v, bool):
        return v
    return v


def _norm_rows(rows: list[tuple]) -> list:
    normed = [tuple(_norm_cell(v) for v in r) for r in rows]
    return sorted(normed, key=repr)


def execution_match(con, gen_sql: str, gold_sql: str) -> tuple[bool, str | None]:
    """Return (matched, error). error is set when the generated SQL fails to run."""
    try:
        gen_rows = con.execute(gen_sql).fetchall()
    except Exception as exc:  # generated SQL invalid
        return False, f"gen_error: {exc}"
    try:
        gold_rows = con.execute(gold_sql).fetchall()
    except Exception as exc:  # pragma: no cover - gold must be valid
        return False, f"gold_error: {exc}"
    return _norm_rows(gen_rows) == _norm_rows(gold_rows), None


def gold_solver(q: dict) -> str:
    return q["gold_sql"]


def run(con, solver: Solver, questions: list[dict] | None = None) -> list[dict]:
    questions = questions or load_questions()
    results = []
    for q in questions:
        gen = solver(q)
        matched, err = execution_match(con, gen, q["gold_sql"])
        results.append({"id": q["id"], "lang": q["lang"], "ok": matched,
                        "error": err, "gen_sql": gen, "question": q["question"]})
    return results


def summarize(results: list[dict]) -> dict:
    total = len(results)
    passed = sum(r["ok"] for r in results)
    by_lang: dict[str, list[int]] = {}
    for r in results:
        agg = by_lang.setdefault(r["lang"], [0, 0])
        agg[1] += 1
        agg[0] += int(r["ok"])
    return {
        "total": total, "passed": passed,
        "accuracy": passed / total if total else 0.0,
        "by_lang": {k: {"passed": v[0], "total": v[1], "acc": v[0] / v[1] if v[1] else 0}
                    for k, v in by_lang.items()},
        "failures": [{"id": r["id"], "lang": r["lang"], "error": r["error"],
                      "question": r["question"]} for r in results if not r["ok"]],
    }


def print_report(summary: dict) -> None:
    print(f"\nNL->SQL eval: {summary['passed']}/{summary['total']} "
          f"({summary['accuracy'] * 100:.1f}%)")
    for lang, s in sorted(summary["by_lang"].items()):
        print(f"  {lang.upper()}: {s['passed']}/{s['total']} ({s['acc'] * 100:.1f}%)")
    if summary["failures"]:
        print("  failures:")
        for f in summary["failures"]:
            tail = f" [{f['error']}]" if f["error"] else ""
            print(f"    - {f['id']} ({f['lang']}): {f['question'][:60]}{tail}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args()
    con = duckdb.connect(args.db, read_only=True)
    results = run(con, gold_solver)
    print_report(summarize(results))
    con.close()


if __name__ == "__main__":
    main()
