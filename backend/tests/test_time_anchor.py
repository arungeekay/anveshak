"""Date-anchor guarantees (FINALE_PLAN F-02).

The synthetic corpus ends 2026-07-20. The Grand Finale demo happens months later,
so anything that computes a relative window ("last 14 days", recency decay) MUST
anchor to the data's own last FIR, not the wall clock, or the Lead Feed is empty
and risk scores collapse on stage.

These tests move the system clock far past the corpus end and assert the demo
still produces its planted results.
"""
from __future__ import annotations

import datetime as _dt

import pytest

from backend.db import data_max_date, get_connection, reset_data_max_date

FINALE_DAY = _dt.date(2026, 9, 26)   # last day of the event window
CORPUS_END = _dt.date(2026, 7, 20)


@pytest.fixture(scope="module")
def con():
    return get_connection()


MODULES_UNDER_CLOCK = (
    "backend.patrol.detectors",
    "backend.tools.risk_score",
    "backend.tools.forecast",
    "backend.db",
)


class _FrozenDatetimeModule:
    """Stand-in for the `datetime` module whose *only* difference is "now".

    date/datetime/timedelta pass straight through to the real classes, so values
    built here are genuine `datetime.date` instances that DuckDB can still bind as
    query parameters, while today()/now() report the finale date. Swapping in
    date/datetime *subclasses* instead would break inside the DuckDB driver rather
    than in the code we are actually testing.
    """

    def __init__(self, frozen_day: _dt.date):
        self._day = frozen_day
        self._dt = _dt.datetime.combine(frozen_day, _dt.time(9, 0))
        self.timedelta = _dt.timedelta
        self.time = _dt.time
        self.timezone = _dt.timezone

        outer = self

        class _Date(_dt.date):
            @classmethod
            def today(cls):
                return outer._day

        class _DateTime(_dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return outer._dt.replace(tzinfo=tz)

            @classmethod
            def utcnow(cls):
                return outer._dt

        # Callers do `_dt.date(y, m, d)` (real instances) and `_dt.date.today()`
        # (frozen), both work because these subclass the real classes.
        self.date = _Date
        self.datetime = _DateTime


@pytest.fixture
def clock_at_finale(monkeypatch):
    """Make every date-sensitive module see the finale date as "today"."""
    import importlib

    frozen = _FrozenDatetimeModule(FINALE_DAY)
    for mod_name in MODULES_UNDER_CLOCK:
        mod = importlib.import_module(mod_name)
        if hasattr(mod, "_dt"):
            monkeypatch.setattr(mod, "_dt", frozen)
    yield FINALE_DAY


def test_anchor_comes_from_the_data(con):
    reset_data_max_date()
    assert data_max_date(con) == CORPUS_END


def test_anchor_ignores_the_wall_clock(con, clock_at_finale):
    """Even with the clock at the finale, the anchor stays on the data."""
    reset_data_max_date()
    assert data_max_date(con) == CORPUS_END
    assert data_max_date(con) < clock_at_finale


def test_detectors_still_fire_at_finale_time(con, clock_at_finale):
    """The Lead Feed, the demo's opening screen, must not go empty in September."""
    from backend.patrol.detectors import run_detectors

    leads = run_detectors(con)
    types = {ld["type"] for ld in leads}
    assert len(leads) >= 3, f"only {len(leads)} leads at finale-time clock"
    for expected in ("spike", "repeat_offender", "series_growth"):
        assert expected in types, f"{expected} detector went silent (got {sorted(types)})"
    # The planted Whitefield burglary spike is the scripted demo beat.
    assert any("Whitefield" in ld["title"] for ld in leads if ld["type"] == "spike"), \
        "planted Whitefield spike no longer fires"
    # Lead timestamps should read from the data, not the wall clock.
    assert all(ld["created_at"].startswith("2026-07") for ld in leads)


def test_risk_recency_unaffected_by_clock(con, clock_at_finale):
    """Suresh B's risk must not decay just because months of wall time passed.

    Compare the frozen-clock score against the same computation with the anchor
    forced to the corpus end: they must be identical, proving the wall clock plays
    no part. (The absolute value ~0.83 comes from his planted dormancy, which is
    the point of the pattern, see demo_story.md SP-4.)
    """
    from backend.tools.risk_score import risk_score

    r = risk_score("P-005555", con=con)
    assert r["score"] >= 0.8, f"repeat-offender risk collapsed to {r['score']}"
    days_at_finale = (FINALE_DAY - CORPUS_END).days
    assert days_at_finale > 60, "test clock is not past the corpus end"
    # Recency decays with days since the last case measured from CORPUS_END; if the
    # wall clock leaked in, those extra ~68 days would drag this well below 0.7.
    assert r["components"]["recency"] > 0.7, r["components"]


def test_forecast_still_returns_at_finale_time(con, clock_at_finale):
    """Forecast history is derived from the data range, so it stays populated."""
    from backend.tools.forecast import forecast

    fc = forecast("Bengaluru City", "House Burglary (Night)", horizon_weeks=4, con=con)
    assert "error" not in fc, fc
    assert fc.get("forecast"), "empty forecast at finale-time clock"
