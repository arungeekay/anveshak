"""Catalyst platform reporting (F-21).

The competition mandates Catalyst and Zoho engineers judge it, so the platform
claim is inspectable rather than asserted. The property that matters: a service is
only reported `live` when something about the running process proves it.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.platform_services import CATALOGUE, platform_status


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_every_catalogued_service_is_reported():
    d = platform_status(False)
    assert d["total"] == len(CATALOGUE)
    assert {s["service"] for s in d["services"]} == {n for n, _ in CATALOGUE}
    for s in d["services"]:
        assert s["used_for"], f"{s['service']} has no stated purpose"
        assert s["status"] in ("live", "integrated", "configured")


def test_appsail_is_not_claimed_live_off_platform(monkeypatch):
    """Running locally, AppSail must not be reported as live."""
    monkeypatch.delenv("X_ZOHO_CATALYST_LISTEN_PORT", raising=False)
    d = platform_status(False)
    appsail = next(s for s in d["services"] if s["service"] == "AppSail")
    assert appsail["status"] != "live"


def test_appsail_is_live_inside_a_catalyst_container(monkeypatch):
    monkeypatch.setenv("X_ZOHO_CATALYST_LISTEN_PORT", "9000")
    d = platform_status(False)
    appsail = next(s for s in d["services"] if s["service"] == "AppSail")
    assert appsail["status"] == "live"


def test_datastore_status_follows_the_real_connection():
    off = next(s for s in platform_status(False)["services"]
               if s["service"] == "Data Store")
    on = next(s for s in platform_status(True)["services"]
              if s["service"] == "Data Store")
    assert off["status"] == "integrated"
    assert on["status"] == "live"


def test_quickml_reflects_the_configured_backend(monkeypatch):
    from backend.config import settings
    monkeypatch.setattr(settings, "llm_backend", "ollama")
    d = platform_status(False)
    q = next(s for s in d["services"] if s["service"].startswith("QuickML"))
    assert q["status"] != "live", "must not claim QuickML while using another backend"


def test_trust_metrics_expose_the_platform(client):
    cat = client.get("/api/trust/metrics").json()["catalyst"]
    assert cat["platform"] == "Zoho Catalyst"
    assert cat["total"] >= 10
    assert "No external inference API" in cat["mandate"]
    assert sum(cat["counts"].values()) == cat["total"]
