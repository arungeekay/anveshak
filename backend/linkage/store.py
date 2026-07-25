"""In-memory store of discovered series + analyst feedback (contracts.md §3).

Discovery is cached; rescan recomputes from the DuckDB mirror. Feedback flips a
hypothesis status and is retained as a label (used for future supervised tuning).
"""
from __future__ import annotations

import threading

from .engine import discover


class SeriesStore:
    def __init__(self) -> None:
        self._series: dict[str, dict] = {}
        self._loaded = False
        # Discovery (HDBSCAN over ~15k cases) takes tens of seconds. Serialize it so
        # concurrent cold requests don't stampede into N parallel full scans; the
        # first caller computes, the rest wait and reuse the cached result.
        self._lock = threading.Lock()

    def rescan(self, con) -> list[dict]:
        with self._lock:
            self._series = {h["series_id"]: h for h in discover(con)}
            self._loaded = True
        return self.all(con)

    def ensure(self, con) -> None:
        if self._loaded:
            return
        with self._lock:
            if not self._loaded:  # double-checked: another thread may have loaded it
                self._series = {h["series_id"]: h for h in discover(con)}
                self._loaded = True

    def all(self, con) -> list[dict]:
        self.ensure(con)
        return sorted(self._series.values(), key=lambda h: h["confidence"], reverse=True)

    def get(self, con, series_id: str) -> dict | None:
        self.ensure(con)
        return self._series.get(series_id)

    def containing(self, con, case_id: int) -> list[dict]:
        self.ensure(con)
        return [h for h in self.all(con) if case_id in h["case_ids"]]

    def feedback(self, con, series_id: str, verdict: str, note: str = "") -> dict | None:
        self.ensure(con)
        h = self._series.get(series_id)
        if not h:
            return None
        h["status"] = "confirmed" if verdict == "confirm" else "rejected"
        h.setdefault("feedback", []).append({"verdict": verdict, "note": note})
        return h


store = SeriesStore()
