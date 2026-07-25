"""Lead feed store (contracts.md §5). Populated by POST /api/leads/run."""
from __future__ import annotations

import threading

from .detectors import run_detectors


class LeadStore:
    def __init__(self) -> None:
        self._leads: list[dict] = []
        self._loaded = False
        # Detectors (STL residual + repeat-offender + series-growth) take tens of
        # seconds; serialize so concurrent cold requests don't all recompute.
        self._lock = threading.Lock()

    def run(self, con) -> list[dict]:
        with self._lock:
            self._leads = run_detectors(con)
            self._loaded = True
        return self._leads

    def ensure(self, con) -> list[dict]:
        if self._loaded:
            return self._leads
        with self._lock:
            if not self._loaded:
                self._leads = run_detectors(con)
                self._loaded = True
        return self._leads

    def all(self) -> list[dict]:
        return self._leads


leads_store = LeadStore()
