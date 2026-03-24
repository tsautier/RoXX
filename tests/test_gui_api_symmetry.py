from fastapi.testclient import TestClient

import roxx.web.app as web_app


def allow_role(monkeypatch, role="superadmin"):
    auth = {"username": "alice", "status": "active", "role": role}
    monkeypatch.setattr("roxx.core.auth.rbac.get_auth_context", lambda request: auth)
    monkeypatch.setattr(web_app, "get_auth_context", lambda request: auth)


def test_system_settings_api_round_trip(monkeypatch):
    allow_role(monkeypatch, "superadmin")

    captured = {}
    monkeypatch.setattr(
        "roxx.core.auth.config_db.ConfigManager.get_system_settings",
        lambda: {"server_name": "Test Node", "radius_auth_port": "1812"},
    )
    monkeypatch.setattr(
        "roxx.core.auth.config_db.ConfigManager.update_system_settings",
        lambda settings: captured.update(settings) or True,
    )

    client = TestClient(web_app.app)

    response = client.get("/api/system/settings")
    assert response.status_code == 200
    assert response.json()["server_name"] == "Test Node"

    update = client.put("/api/system/settings", json={
        "server_name": "Updated Node",
        "radius_auth_port": 1912,
        "radius_acct_port": 1913,
        "log_level": "warning",
        "audit_retention_days": 30,
        "debug_mode": True,
    })
    assert update.status_code == 200
    assert captured["server_name"] == "Updated Node"
    assert captured["radius_auth_port"] == "1912"
    assert captured["radius_acct_port"] == "1913"
    assert captured["log_level"] == "WARNING"
    assert captured["audit_retention_days"] == "30"
    assert captured["debug_mode"] == "true"


def test_observability_and_integration_pages_render(monkeypatch):
    allow_role(monkeypatch, "superadmin")
    client = TestClient(web_app.app)

    observability = client.get("/system/observability")
    tools = client.get("/tools/integrations")

    assert observability.status_code == 200
    assert "Observability & Health" in observability.text
    assert tools.status_code == 200
    assert "Integration Tools" in tools.text
