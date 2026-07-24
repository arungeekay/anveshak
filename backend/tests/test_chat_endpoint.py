"""T09: /api/chat returns contract-shaped JSON (engine + LLM stubbed for determinism)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api import chat as chat_api
from backend.main import app
from backend.nl2sql.engine import NLResult

client = TestClient(app)


@pytest.fixture
def stub(monkeypatch):
    fake = NLResult(
        sql="SELECT COUNT(*) FROM vw_case_360 WHERE district='Bengaluru City'",
        columns=["count_star()"], rows=[(1234,)], row_count=1, truncated=False,
        attempts=1, repaired=False,
    )
    monkeypatch.setattr(chat_api, "db_status", lambda: {"db": "loaded", "cases": 15405})
    monkeypatch.setattr(chat_api.engine, "run", lambda con, msg, **k: fake)
    monkeypatch.setattr(chat_api, "compose_answer", lambda *a, **k: "There are 1,234 cases.")
    monkeypatch.setattr(chat_api, "write_audit", lambda *a, **k: 991)
    monkeypatch.setattr(chat_api, "get_connection", lambda: None)


def test_chat_contract_shape(stub):
    resp = client.post("/api/chat", json={"session_id": "s1", "message": "how many cases?", "lang": "en"})
    assert resp.status_code == 200
    body = resp.json()
    for key in ("answer_text", "render_specs", "evidence", "confidence", "audit_id"):
        assert key in body
    assert body["evidence"]["tool"] == "run_sql"
    assert body["evidence"]["sql"].upper().startswith("SELECT")
    assert body["confidence"] == "high"
    assert body["render_specs"][-1]["type"] == "table"


def test_chat_db_not_loaded(monkeypatch):
    monkeypatch.setattr(chat_api, "db_status", lambda: {"db": "not_loaded", "cases": 0})
    resp = client.post("/api/chat", json={"message": "hi"})
    assert resp.status_code == 200
    assert "error" in resp.json()
