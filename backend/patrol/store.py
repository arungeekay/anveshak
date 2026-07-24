"""Lead feed store (contracts.md §5). Populated by POST /api/leads/run."""
from __future__ import annotations

from .detectors import run_detectors


class LeadStore:
    def __init__(self) -> None:
        self._leads: list[dict] = []

    def run(self, con) -> list[dict]:
        self._leads = run_detectors(con)
        return self._leads

    def all(self) -> list[dict]:
        return self._leads


leads_store = LeadStore()
