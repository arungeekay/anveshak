"""T17 verify: Investigation Cell produces a complete pack; SSE event order correct."""
from __future__ import annotations

import time

import pytest

from backend.agents.pipeline import AGENTS, investigate
from backend.graph import engine as graph_engine
from backend.linkage.store import store
from backend.pdf.pack_render import render_pack_html
from data_engine.build import build_dataset


@pytest.fixture(scope="module")
def con():
    c, _ = build_dataset(seed=42, n_cases=2500, out_path=None, embeddings=True, export_csv=False)
    store.rescan(c)                # fresh series discovery on this connection
    graph_engine.cache.rebuild(c)  # fresh graph on this connection
    return c


@pytest.fixture(scope="module")
def run(con):
    t0 = time.time()
    events = list(investigate(con, "SH-07"))
    return events, time.time() - t0


def test_completes_under_two_minutes(run):
    _events, elapsed = run
    assert elapsed < 120, f"pipeline took {elapsed:.1f}s"


def test_all_six_agents_stream(run):
    events, _ = run
    steps = [d["agent"] for ev, d in events if ev == "agent_step"]
    for agent in AGENTS:
        assert agent in steps, f"{agent} did not stream"
    # ordered: case_officer first, forecaster last among agents
    order = [a for a in steps if a in AGENTS]
    assert order[0] == "case_officer"
    assert order[-1] == "forecaster"


def test_pack_ready_is_complete(run):
    events, _ = run
    ev, data = events[-1]
    assert ev == "pack_ready"
    assert data["pdf_url"]
    pack = data["pack"]
    assert len(pack["timeline"]) >= 12
    assert pack["suspects_ranked"], "no suspects ranked"
    assert any(s["act"] == "BNS" and s["section"] == "304(2)"
               for s in pack["legal"]["sections_invoked"])
    assert pack["forecast"]["next_window"]


def test_ravi_ranked_top(run):
    events, _ = run
    pack = events[-1][1]["pack"]
    assert pack["suspects_ranked"][0]["person_key"] == "P-004412"  # Ravi K


def test_pack_html_renders(run):
    pack = run[0][-1][1]["pack"]
    doc = render_pack_html(pack)
    assert "Investigation Pack" in doc and "SH-07" in doc
