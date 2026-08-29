"""FIR intake and free-text similarity (FINALE_PLAN F-06).

The demo beat: a judge describes a chain snatching in their own words and ANVESHAK
embeds it live, re-runs linkage, and reports that it joined SH-07. These tests prove
that works from a *paraphrase* (never corpus text) and that the state is fully
restorable between rehearsals.

Skipped without models/minilm-onnx (see scripts/fetch_onnx_model.py) unless
sentence-transformers is importable as the dev fallback.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.db import get_connection
from backend.embeddings.onnx_embedder import available
from backend.linkage.store import store
from backend.main import app

pytestmark = pytest.mark.skipif(
    not available(), reason="no embedding backend (run scripts/fetch_onnx_model.py)")

# Deliberately NOT the planted wording: same modus operandi, a witness's phrasing.
PARAPHRASED_SNATCH = (
    "Yesterday evening around 7:30 pm my mother was walking by herself near the "
    "market when two men riding a black motorbike came up from behind her. The man "
    "sitting at the back grabbed her gold chain and they rode off fast the wrong "
    "way down the one-way road. Both had their helmet visors pulled down.")

UNRELATED = (
    "The complainant reports that his office laptop was taken from a locked cabin "
    "during working hours; the lock was found intact and no forced entry was seen.")


@pytest.fixture
def client():
    c = TestClient(app)
    con = get_connection()
    store.ensure(con)
    yield c
    c.post("/api/intake/reset")  # always restore the pristine corpus


def _sh07_size(con) -> int:
    h = store.get(con, "SH-07")
    return len(h["case_ids"]) if h else 0


def test_paraphrased_fir_joins_the_series(client):
    """The flagship moment: unseen wording lands in SH-07 and grows it by one."""
    con = get_connection()
    before = _sh07_size(con)
    assert before >= 14, f"SH-07 unexpectedly small ({before}) before intake"

    r = client.post("/api/intake", json={
        "narrative": PARAPHRASED_SNATCH, "district": "Bengaluru City",
        "police_station": "Jayanagar PS", "lang": "en"})
    assert r.status_code == 200, r.text
    d = r.json()

    assert d["embedded"] is True
    assert d["case_id"] > 15405, "new case must be appended, not overwrite the corpus"
    assert "SH-07" in d["joined_series"], f"did not join SH-07: {d['joined_series']}"
    assert _sh07_size(con) == before + 1

    joined = next(s for s in d["series"] if s["series_id"] == "SH-07")
    assert joined["case_count"] == before + 1
    assert joined["confidence"] >= 0.8


def test_intake_is_fast_enough_for_the_gateway(client):
    """Embed + rescan must finish inside the ~30s request cut."""
    r = client.post("/api/intake", json={
        "narrative": PARAPHRASED_SNATCH, "district": "Bengaluru City",
        "police_station": "Jayanagar PS"})
    assert r.status_code == 200
    assert r.json()["rescan_ms"] < 25_000, r.json()["rescan_ms"]


def test_unrelated_fir_does_not_join_the_snatching_series(client):
    """Guards against a linkage that just accepts anything."""
    r = client.post("/api/intake", json={
        "narrative": UNRELATED, "district": "Bengaluru City",
        "police_station": "Jayanagar PS", "crime_sub_head": "Theft"})
    assert r.status_code == 200
    assert "SH-07" not in r.json()["joined_series"]


def test_reset_restores_the_pristine_corpus(client):
    con = get_connection()
    before = _sh07_size(con)
    client.post("/api/intake", json={
        "narrative": PARAPHRASED_SNATCH, "district": "Bengaluru City",
        "police_station": "Jayanagar PS"})
    assert _sh07_size(con) == before + 1

    r = client.post("/api/intake/reset")
    assert r.status_code == 200
    assert r.json()["cases"] == 15405
    assert _sh07_size(con) == before


def test_similar_by_text_finds_the_series_cases(client):
    """Free-text search over never-before-seen wording."""
    r = client.post("/api/similar/by_text",
                    json={"narrative": PARAPHRASED_SNATCH, "k": 5})
    assert r.status_code == 200
    matches = r.json()["matches"]
    assert len(matches) == 5
    assert matches[0]["cosine"] > 0.7
    subs = [m["crime_sub_head"] for m in matches]
    assert subs.count("Chain Snatching") >= 3, subs
    assert matches[0]["cosine"] >= matches[-1]["cosine"], "not ranked by similarity"


def test_intake_rejects_unknown_district(client):
    r = client.post("/api/intake", json={
        "narrative": PARAPHRASED_SNATCH, "district": "Atlantis"})
    assert r.status_code == 400


def test_masters_feed_the_form(client):
    d = client.get("/api/masters").json()
    assert "Bengaluru City" in d["districts"]
    assert "Jayanagar PS" in d["police_stations"]["Bengaluru City"]
    assert "Chain Snatching" in d["crime_sub_heads"]
