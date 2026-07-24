"""T14 verify: CrimeGraph canned queries on planted data (no embeddings needed)."""
from __future__ import annotations

import pytest

from backend.graph import engine
from data_engine.build import build_dataset


@pytest.fixture(scope="module")
def built():
    con, truth = build_dataset(seed=42, n_cases=800, out_path=None, embeddings=False, export_csv=False)
    engine.cache.rebuild(con)
    return con, truth


def test_prakash_hub_has_22_spokes(built):
    con, truth = built
    res = engine.ego_network(con, truth["SP2"]["hub"], depth=1)
    cases = [n for n in res["nodes"] if n["kind"] == "case"]
    assert len(cases) == 22, f"expected 22-spoke hub, got {len(cases)}"


def test_community_of_sp1_contains_ring(built):
    con, truth = built
    solved = truth["SP1"]["solved_case_ids"][0]
    res = engine.community_of(con, solved)
    members = set(res["communities"][0]["person_keys"]) if res["communities"] else set()
    ravi, manju, _third = truth["SP1"]["ring"]
    assert ravi in members and manju in members, f"ring not in community: {members}"


def test_path_between_ring_members(built):
    con, truth = built
    ravi, manju, _ = truth["SP1"]["ring"]
    res = engine.path_between(con, ravi, manju)
    assert res["highlight_path"], "no path between co-accused ring members"
    assert res["highlight_path"][0] == ravi and res["highlight_path"][-1] == manju
