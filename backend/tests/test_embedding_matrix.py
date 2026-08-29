"""Embedding-matrix cache + investigation latency budget (FINALE_PLAN F-03).

The AppSail gateway severs SSE connections at ~40s. The Investigation Cell calls
similar_cases 16x per run; when each call re-read all 15k vectors from DuckDB the
run took ~65s and `pack_ready` never reached the browser. These tests lock in both
the correctness of the cached matrix and the latency headroom.
"""
from __future__ import annotations

import time

import numpy as np
import pytest

from backend.db import get_connection
from backend.embeddings import matrix
from backend.tools.similar_cases import similar_cases

SERIES_CASE = 4001  # a planted SH-07 chain-snatching case
GATEWAY_BUDGET_S = 35.0  # hard SSE cut is ~40s; keep headroom


@pytest.fixture(scope="module")
def con():
    c = get_connection()
    matrix.ensure(c)
    return c


def test_matrix_loads_every_case(con):
    n_rows = con.execute(
        "SELECT COUNT(*) FROM CaseMOVector WHERE embedding IS NOT NULL").fetchone()[0]
    assert matrix.size() == n_rows > 0


def test_rows_are_l2_normalised(con):
    v = matrix.vector_for(con, SERIES_CASE)
    assert v is not None
    assert np.isclose(np.linalg.norm(v), 1.0, atol=1e-4)


def test_search_matches_bruteforce(con):
    """The cached search must return exactly what a full scan would."""
    q = matrix.vector_for(con, SERIES_CASE)
    rows = con.execute(
        "SELECT CaseMasterID, embedding FROM CaseMOVector "
        "WHERE CaseMasterID <> ? AND embedding IS NOT NULL", [SERIES_CASE]).fetchall()
    ids = np.array([r[0] for r in rows])
    mat = np.asarray([r[1] for r in rows], dtype=float)
    mat /= (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
    sims = mat @ np.asarray(q, dtype=float)
    expected = [(int(ids[i]), round(float(sims[i]), 3)) for i in np.argsort(-sims)[:5]]
    got = [(d["case_id"], d["similarity"]) for d in similar_cases(SERIES_CASE, k=5, con=con)]
    assert got == expected


def test_similar_cases_is_fast_when_warm(con):
    similar_cases(SERIES_CASE, k=5, con=con)  # ensure warm
    t0 = time.time()
    for _ in range(10):
        similar_cases(SERIES_CASE, k=5, con=con)
    per_call = (time.time() - t0) / 10
    # Was ~2.5s/call before caching; 0.2s leaves room for slow CI machines.
    assert per_call < 0.2, f"similar_cases too slow when warm: {per_call:.3f}s/call"


def test_add_appends_new_case(con):
    """FIR intake appends to the cache without a full rebuild."""
    before = matrix.size()
    fake_id = 10**9  # far outside real ids
    vec = np.ones(matrix.vector_for(con, SERIES_CASE).shape[0], dtype=np.float32)
    try:
        matrix.add(con, fake_id, vec)
        assert matrix.size() == before + 1
        assert matrix.vector_for(con, fake_id) is not None
        hits = matrix.search(con, vec, k=1)
        assert hits and hits[0][0] == fake_id
    finally:
        matrix.reset()
        matrix.ensure(con)


@pytest.mark.slow
def test_investigation_fits_gateway_budget(con):
    """Full 6-agent run must finish well inside the ~40s SSE cut."""
    from backend.agents.pipeline import investigate
    from backend.graph import engine
    from backend.linkage.store import store

    store.ensure(con)
    engine.cache.ensure(con)  # prewarmed in production (serve.py)

    t0 = time.time()
    final = None
    for event, data in investigate(con, "SH-07"):
        final = (event, data)
    elapsed = time.time() - t0

    assert final and final[0] == "pack_ready", f"stream ended on {final[0] if final else None}"
    assert final[1].get("pack"), "no pack assembled"
    assert elapsed < GATEWAY_BUDGET_S, (
        f"investigation took {elapsed:.1f}s (budget {GATEWAY_BUDGET_S}s), "
        "the SSE would be severed before pack_ready")
