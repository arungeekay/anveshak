"""T12 verify: linkage precision/recall against planted truth.

SH-07 (chain-snatching serial) must be discovered cold with hypothesis precision
>=0.8 and recall >=12/14 (the 2 charge-sheeted cases are excluded from the
Under-Investigation candidate universe). SP-2 (fraud) must NOT merge into SH-07.
"""
from __future__ import annotations

import pytest

from backend.linkage.engine import discover
from data_engine.build import build_dataset

N_BG = 2500


@pytest.fixture(scope="module")
def discovered():
    con, truth = build_dataset(seed=42, n_cases=N_BG, out_path=None, embeddings=True, export_csv=False)
    hyps = discover(con)
    con.close()
    return hyps, truth


def _sh07(hyps):
    for h in hyps:
        if h["series_id"] == "SH-07":
            return h
    return None


def test_sh07_discovered(discovered):
    hyps, _ = discovered
    h = _sh07(hyps)
    assert h is not None, "SH-07 chain-snatching series not discovered"
    assert h["crime_sub_head"] == "Chain Snatching"
    assert {"Bengaluru City", "Tumakuru", "Mandya"}.issubset(set(h["districts"]))


def test_sh07_precision_and_recall(discovered):
    hyps, truth = discovered
    h = _sh07(hyps)
    members = set(h["case_ids"])
    planted = set(truth["SP1"]["case_ids"])
    tp = members & planted
    precision = len(tp) / len(members)
    recall = len(tp)  # out of 14 planted (12 are UI-eligible)
    print(f"\nSH-07: size={len(members)} precision={precision:.2f} recall={recall}/14 "
          f"confidence={h['confidence']}")
    assert precision >= 0.8, f"precision {precision:.2f} < 0.8 (members={len(members)})"
    assert recall >= 12, f"recall {recall}/14 < 12"


def test_sp2_not_merged_into_sh07(discovered):
    hyps, truth = discovered
    h = _sh07(hyps)
    sp2 = set(truth["SP2"]["case_ids"])
    assert set(h["case_ids"]).isdisjoint(sp2), "SP-2 fraud cases leaked into SH-07"


def test_links_have_evidence(discovered):
    hyps, _ = discovered
    h = _sh07(hyps)
    assert h["links"], "series must expose link evidence"
    assert any(link["shared_features"] for link in h["links"])
