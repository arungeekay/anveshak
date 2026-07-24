"""T05 verify (fast, in-memory): DuckDB build + views + MO vectors.

Uses a small background volume with real embeddings so the CaseMOVector pipeline
and analyst views are exercised end-to-end. The full 15k on-disk build is produced
by `python -m data_engine.build`.
"""
from __future__ import annotations

import pytest

from data_engine.build import build_dataset

EMBED_DIM = 384  # paraphrase-multilingual-MiniLM-L12-v2


@pytest.fixture(scope="module")
def con():
    c, _ = build_dataset(seed=42, n_cases=300, out_path=None, embeddings=True, export_csv=False)
    yield c
    c.close()


def _n(con, sql):
    return con.execute(sql).fetchone()[0]


def test_case_and_view_counts_match(con):
    n_cases = _n(con, "SELECT COUNT(*) FROM CaseMaster")
    n_view = _n(con, "SELECT COUNT(*) FROM vw_case_360")
    assert n_cases == n_view
    assert n_cases >= 300  # background + planted


def test_mo_vector_count_equals_case_count(con):
    assert _n(con, "SELECT COUNT(*) FROM CaseMOVector") == _n(con, "SELECT COUNT(*) FROM CaseMaster")


def test_embedding_dimensionality(con):
    assert _n(con, "SELECT len(embedding) FROM CaseMOVector LIMIT 1") == EMBED_DIM


def test_mo_features_populated_for_chain_snatching(con):
    # Planted chain-snatching cases should carry vehicle:motorcycle + target:gold_chain.
    hit = _n(con, """
        SELECT COUNT(*) FROM CaseMOVector v JOIN vw_case_360 c USING (CaseMasterID)
        WHERE c.crime_sub_head='Chain Snatching'
          AND v.mo_features LIKE '%motorcycle%' AND v.mo_features LIKE '%gold_chain%'
    """)
    assert hit >= 8


def test_three_views_spot_check(con):
    assert _n(con, "SELECT COUNT(*) FROM vw_accused_history") > 0
    assert _n(con, "SELECT COUNT(*) FROM vw_station_monthly") > 0
    assert _n(con, "SELECT COUNT(*) FROM vw_coaccusal_edges") >= 1
