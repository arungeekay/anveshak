"""Intent router keyword classification (deterministic, no DB for non-network)."""
from __future__ import annotations

from backend.nl2sql.router import route


def test_linkage_intent():
    assert route(None, "Are any of these cases connected?")[0] == "linkage"


def test_forecast_intent_with_entities():
    intent, params = route(None, "Where will chain snatching strike next in Tumakuru?")
    assert intent == "forecast"
    assert params["district"] == "Tumakuru"
    assert params["crime_sub_head"] == "Chain Snatching"


def test_hotspots_intent():
    assert route(None, "Show a map of house burglary in Mysuru")[0] == "hotspots"


def test_risk_rank_intent():
    intent, params = route(None, "Who are the top repeat offenders in Bengaluru City?")
    assert intent == "risk_rank"
    assert params["district"] == "Bengaluru City"


def test_default_is_run_sql():
    assert route(None, "How many murders were there in Mysuru in 2024?")[0] == "run_sql"
