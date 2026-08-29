"""Person 360 (FINALE_PLAN F-13).

The page an investigating officer lives in: one name, the whole criminal footprint.
Assembled from existing deterministic tools (ADR-2), accused history, risk scoring,
CrimeGraph, never from the model.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

HUB = "P-007001"        # Prakash Rao, the investment-fraud hub (demo_story SP-2)
REPEAT = "P-005555"     # Suresh B, the escalating repeat offender (SP-4)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_search_ranks_the_most_connected_namesake_first(client):
    """'Prakash Rao' matches several people; the hub must come first."""
    r = client.get("/api/person", params={"q": "Prakash Rao"})
    assert r.status_code == 200
    hits = r.json()
    assert hits, "no matches for a known name"
    assert hits[0]["person_key"] == HUB, [h["person_key"] for h in hits[:3]]
    assert hits[0]["n_cases"] >= hits[-1]["n_cases"], "not ordered by case count"


def test_search_rejects_a_too_short_query(client):
    assert client.get("/api/person", params={"q": "a"}).status_code == 400


def test_unknown_person_is_404(client):
    assert client.get("/api/person/P-000000").status_code == 404


def test_hub_profile_is_complete(client):
    d = client.get(f"/api/person/{HUB}").json()
    assert d["name"] == "Prakash Rao"
    assert d["stats"]["total_cases"] >= 14
    assert len(d["stats"]["districts"]) >= 3, "hub should span districts"
    assert d["stats"]["crime_types"][0][0] == "Cheating / Online Fraud"
    assert d["risk"]["score"] > 0.5
    # The CrimeGraph exhibit is what makes the fraud web visible.
    assert len(d["network"].get("nodes", [])) >= 20


def test_repeat_offender_profile_matches_the_planted_pattern(client):
    d = client.get(f"/api/person/{REPEAT}").json()
    assert d["name"] == "Suresh B"
    assert d["risk"]["score"] >= 0.8
    comps = d["risk"]["components"]
    assert set(comps) == {"recency", "frequency", "gravity", "centrality"}
    assert d["stats"]["arrests"] >= 1, "SP-4 persona was arrested and released"


def test_age_is_reported_as_a_range_not_a_false_precision(client):
    """AgeYear differs across FIRs for the same person (real CCTNS noise), so the
    profile must not present one arbitrary value as fact."""
    d = client.get(f"/api/person/{HUB}").json()
    assert "–" in d["age_recorded"], d["age_recorded"]
    assert d["dob"], "the stable identity field should still be surfaced"


def test_profile_excludes_protected_attributes(client):
    """ADR-9: religion/caste must never appear in a person profile."""
    body = client.get(f"/api/person/{HUB}").text.lower()
    for banned in ("religion", "caste", "communal"):
        assert banned not in body, f"{banned} leaked into the profile payload"
