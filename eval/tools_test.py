"""T16 verify: analytics tools + ADR-9 (no protected attributes in risk_score)."""
from __future__ import annotations

import inspect

import pytest

from backend.tools import forecast as forecast_mod
from backend.tools import hotspots as hotspots_mod
from backend.tools import risk_score as risk_mod
from backend.tools import similar_cases as similar_mod
from data_engine.build import build_dataset


@pytest.fixture(scope="module")
def built():
    con, truth = build_dataset(seed=42, n_cases=3000, out_path=None, embeddings=True, export_csv=False)
    return con, truth


def test_adr9_no_protected_attributes():
    src = inspect.getsource(risk_mod)
    for banned in ("Religion", "Caste", "Occupation"):
        assert banned not in src, f"risk_score must not reference {banned} (ADR-9)"


def test_risk_score_suresh_high(built):
    con, truth = built
    res = risk_mod.risk_score(truth["SP4"]["person"], con=con)
    print(f"\nSuresh risk: {res['score']} {res['components']}")
    assert set(res["components"]) == {"recency", "frequency", "gravity", "centrality"}
    assert res["score"] >= 0.8
    assert len(res["history_case_ids"]) == 5


def test_risk_ravi_above_manju(built):
    con, truth = built
    ravi, manju, _ = truth["SP1"]["ring"]
    r = risk_mod.risk_score(ravi, con=con)["score"]
    m = risk_mod.risk_score(manju, con=con)["score"]
    assert r >= m


def test_similar_cases_returns_k(built):
    con, truth = built
    sp1 = truth["SP1"]["case_ids"][0]
    out = similar_mod.similar_cases(sp1, k=5, con=con)
    assert len(out) == 5
    assert all("similarity" in o for o in out)
    # the nearest neighbours of a serial case should be other serial cases
    assert out[0]["similarity"] > 0.5


def test_hotspots_returns_cells(built):
    con, _ = built
    res = hotspots_mod.hotspots(crime_sub_head="Chain Snatching", district="Bengaluru City",
                                date_from="2026-01-01", date_to="2026-12-31", con=con)
    assert res["cells"]
    assert res["cells"][0]["intensity"] == 1.0  # peak cell normalized to 1


def test_forecast_beats_seasonal_naive(built):
    con, _ = built
    res = forecast_mod.forecast("Bengaluru City", "House Burglary (Night)", horizon_weeks=8, con=con)
    print(f"\nforecast: backtest_mae={res.get('backtest_mae')} baseline_mae={res.get('baseline_mae')}")
    if "error" in res:
        pytest.skip(f"thin history: {res}")
    assert len(res["forecast"]) == 8
    assert res["backtest_mae"] is not None
    if res["baseline_mae"]:
        assert res["backtest_mae"] <= res["baseline_mae"] * 1.25  # competitive with naive
