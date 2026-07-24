from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    # DB may or may not be built yet; both states are valid.
    assert body["db"] in {"loaded", "not_loaded", "error"}
