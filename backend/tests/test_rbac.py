"""Server-side role scoping (ADR-8, FINALE_PLAN F-09).

The invariant: a scoped role cannot see beyond its unit, and the enforcement lives
in the SQL that actually runs, not in the prompt (which a model may ignore) and
not in the browser (which is not access control).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.auth.scope import Scope, ScopeError, mask_rows, scope_sql
from backend.db import get_connection
from backend.main import app

D1_SQL = ("SELECT COUNT(*) FROM vw_case_360 WHERE crime_sub_head = 'Chain Snatching' "
          "AND district = 'Bengaluru City' AND year(CrimeRegisteredDate) = 2026")


@pytest.fixture(scope="module")
def con():
    return get_connection()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _count(con, scope: Scope) -> int:
    return con.execute(scope_sql(D1_SQL, scope)).fetchone()[0]


def test_scopes_narrow_the_same_question(con):
    """The demo moment: one question, three roles, visibly different answers."""
    statewide = _count(con, Scope("SCRB"))
    district = _count(con, Scope("SP", "Bengaluru City"))
    station = _count(con, Scope("SHO", "Jayanagar PS"))

    assert statewide == 47, statewide
    assert station > 0, "the station scope returned nothing, demo would look broken"
    assert station < statewide, f"SHO ({station}) must see less than SCRB ({statewide})"
    assert district <= statewide


def test_station_scope_cannot_reach_another_station(con):
    """A Jayanagar SHO must not be able to count Whitefield's cases."""
    sql = ("SELECT COUNT(*) FROM vw_case_360 "
           "WHERE police_station = 'Whitefield PS'")
    n = con.execute(scope_sql(sql, Scope("SHO", "Jayanagar PS"))).fetchone()[0]
    assert n == 0, f"scope leaked: SHO saw {n} Whitefield cases"


def test_scope_survives_a_query_that_names_another_district(con):
    """Even asked explicitly about Mysuru, a Bengaluru SP sees nothing there."""
    sql = "SELECT COUNT(*) FROM vw_case_360 WHERE district = 'Mysuru'"
    n = con.execute(scope_sql(sql, Scope("SP", "Bengaluru City"))).fetchone()[0]
    assert n == 0, f"scope leaked: SP saw {n} Mysuru cases"


def test_statewide_roles_are_untouched():
    for role in ("SCRB", "ANALYST"):
        assert scope_sql(D1_SQL, Scope(role)) == D1_SQL


def test_unscopable_query_is_refused_not_silently_widened():
    """Better an honest refusal than data returned outside the caller's scope."""
    with pytest.raises(ScopeError):
        scope_sql("SELECT COUNT(*) FROM CaseMaster", Scope("SHO", "Jayanagar PS"))


def test_analyst_sees_statewide_numbers_but_masked_names(con):
    assert _count(con, Scope("ANALYST")) == _count(con, Scope("SCRB"))
    masked = mask_rows(["full_name", "n"], [["Ravi Kumar", 3]], Scope("ANALYST"))
    assert masked == [["R. K.", 3]]


def test_masking_leaves_non_name_columns_alone():
    rows = mask_rows(["district", "n"], [["Bengaluru City", 5]], Scope("ANALYST"))
    assert rows == [["Bengaluru City", 5]]


def test_person_profile_masks_for_analyst(client):
    plain = client.get("/api/person/P-007001").json()
    masked = client.get("/api/person/P-007001",
                        headers={"X-Anveshak-Role": "ANALYST"}).json()
    assert plain["name"] == "Prakash Rao"
    assert masked["name"] == "P. R."
    # The pseudonymous key is still returned so cases remain correlatable.
    assert masked["person_key"] == plain["person_key"]
    assert masked["stats"]["total_cases"] == plain["stats"]["total_cases"]


def test_unknown_role_falls_back_to_the_narrowest_safe_default(client):
    """A malformed role header must not grant anything unexpected."""
    from backend.auth.scope import from_headers
    assert from_headers({"x-anveshak-role": "SUPERUSER"}).role == "SCRB"
    assert from_headers({}).role == "SCRB"
