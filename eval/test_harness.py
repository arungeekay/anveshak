"""T07 verify: the eval harness runs end-to-end; gold-vs-gold sanity = 100%.

This also proves every one of the 60 gold SQL statements parses and executes against
the schema/views (a syntax/identifier regression guard).
"""
from __future__ import annotations

from data_engine.build import build_dataset
from eval.harness import gold_solver, load_questions, run, summarize


def test_sixty_questions_present():
    qs = load_questions()
    assert len(qs) == 60
    assert sum(q["lang"] == "en" for q in qs) == 45
    assert sum(q["lang"] == "kn" for q in qs) == 15


def test_gold_vs_gold_is_100pct():
    con, _ = build_dataset(seed=42, n_cases=300, out_path=None, embeddings=False, export_csv=False)
    summary = summarize(run(con, gold_solver))
    con.close()
    assert summary["total"] == 60
    assert summary["accuracy"] == 1.0, summary["failures"]
