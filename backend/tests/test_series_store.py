"""SeriesStore logic (feedback, containing) — deterministic, no DB."""
from __future__ import annotations

from backend.linkage.store import SeriesStore


def _store():
    s = SeriesStore()
    s._series = {"SH-01": {"series_id": "SH-01", "case_ids": [1, 2, 3],
                           "confidence": 0.9, "status": "open"}}
    s._loaded = True
    return s


def test_get_and_containing():
    s = _store()
    assert s.get(None, "SH-01")["series_id"] == "SH-01"
    assert s.get(None, "SH-99") is None
    assert s.containing(None, 2)[0]["series_id"] == "SH-01"
    assert s.containing(None, 99) == []


def test_feedback_flips_status():
    s = _store()
    h = s.feedback(None, "SH-01", "confirm", "looks right")
    assert h["status"] == "confirmed"
    assert h["feedback"][0]["verdict"] == "confirm"
    assert s.feedback(None, "SH-99", "reject") is None
