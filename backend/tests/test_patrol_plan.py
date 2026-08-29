"""Patrol Plan and the spoken morning briefing (FINALE_PLAN F-14, F-16)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# --- F-14 patrol plan --------------------------------------------------------

def test_plan_ranks_the_planted_spike_first(client):
    """Whitefield's planted burglary spike is the strongest signal in the district."""
    d = client.get("/api/patrol/plan", params={"district": "Bengaluru City"}).json()
    assert d["items"], "no plan items"
    top = d["items"][0]
    assert top["police_station"] == "Whitefield PS", top["police_station"]
    assert "House Burglary (Night)" in top["focus"], top["focus"]
    assert "night_patrol:spike" in top["sources"]


def test_every_item_is_explainable(client):
    """ADR-2: an officer must be able to audit why a station was ranked."""
    d = client.get("/api/patrol/plan", params={"district": "Bengaluru City"}).json()
    for it in d["items"]:
        assert it["reasons"], f"{it['police_station']} has no stated reason"
        assert it["sources"], f"{it['police_station']} cites no tool"
        assert it["window"], "no deployment window"


def test_background_clusters_do_not_swamp_the_plan(client):
    """Discovery surfaces huge background clusters; they must not dominate.

    Without filtering, a single station accumulated 20+ series and a priority of
    35, the reasoning became unreadable and the focus wrong.
    """
    d = client.get("/api/patrol/plan", params={"district": "Bengaluru City"}).json()
    for it in d["items"]:
        linkage = [s for s in it["sources"] if s.startswith("linkage:")]
        assert len(linkage) <= 4, f"{it['police_station']} cites {len(linkage)} series"
        assert it["priority"] < 15, f"priority {it['priority']} looks inflated"


def test_method_is_stated_honestly(client):
    d = client.get("/api/patrol/plan", params={"district": "Bengaluru City"}).json()
    assert "heuristic" in d["method"].lower()
    assert "does not replace" in d["method"].lower()


def test_unknown_district_is_rejected(client):
    assert client.get("/api/patrol/plan",
                      params={"district": "Atlantis"}).status_code == 400


# --- F-16 morning briefing ---------------------------------------------------

def test_briefing_cites_real_leads(client):
    d = client.get("/api/briefing", params={"lang": "en"}).json()
    assert d["leads_cited"], "briefing cites no leads"
    assert "ANVESHAK" in d["text"]
    assert d["as_of"].startswith("2026-"), d["as_of"]


def test_kannada_briefing_is_in_kannada(client):
    d = client.get("/api/briefing", params={"lang": "kn"}).json()
    assert d["lang"] == "kn"
    kn_chars = sum(1 for ch in d["text"] if "ಀ" <= ch <= "೿")
    assert kn_chars > 40, f"only {kn_chars} Kannada characters"


def test_briefing_numbers_come_from_the_detectors(client):
    """ADR-2: the brief is templated around tool values, never model-authored."""
    d = client.get("/api/briefing", params={"lang": "en"}).json()
    leads = client.get("/api/leads").json()
    assert "no model text" in d["composed_from"]
    # The strongest lead's case count must appear verbatim in the spoken text.
    top = max(leads, key=lambda x: x.get("confidence", 0))
    n_cases = len((top.get("evidence") or {}).get("case_ids") or [])
    assert str(n_cases) in d["text"], f"{n_cases} not cited in: {d['text'][:200]}"
