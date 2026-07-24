"""T20 verify: Night Patrol detectors fire on the planted anomalies."""
from __future__ import annotations

import pytest

from backend.linkage.store import store
from backend.patrol.detectors import run_detectors
from data_engine.build import build_dataset


@pytest.fixture(scope="module")
def result():
    # embeddings not needed: spike + repeat_offender use SQL/geo; series_growth degrades
    # gracefully (no CaseMOVector -> no series).
    con, truth = build_dataset(seed=42, n_cases=2000, out_path=None, embeddings=False, export_csv=False)
    store._loaded = False
    return run_detectors(con), truth


def test_whitefield_spike_fires(result):
    leads, truth = result
    spikes = [ld for ld in leads if ld["type"] == "spike"]
    hit = [ld for ld in spikes if "Whitefield" in ld["title"]]
    assert hit, f"no Whitefield spike among {[s['title'] for s in spikes]}"
    lead = hit[0]
    assert lead["evidence"]["value"] >= 3
    planted = set(truth["SP3"]["live_spike_case_ids"])
    assert set(lead["evidence"]["case_ids"]) & planted, "spike case_ids miss the planted anomaly"


def test_suresh_repeat_offender_fires(result):
    leads, truth = result
    ro = [ld for ld in leads if ld["type"] == "repeat_offender"]
    assert ro, "no repeat_offender lead"
    planted = set(truth["SP4"]["fresh_cluster_case_ids"])
    hit = [ld for ld in ro if set(ld["evidence"]["case_ids"]) & planted]
    assert hit, "repeat_offender did not flag Suresh's fresh cluster"
    assert "Suresh" in hit[0]["title"]


def test_leads_have_contract_shape(result):
    leads, _ = result
    for ld in leads:
        for key in ("lead_id", "type", "title", "evidence", "confidence",
                    "suggested_action", "district", "created_at"):
            assert key in ld
