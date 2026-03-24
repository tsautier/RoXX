from fastapi.testclient import TestClient
import json

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


def test_mfa_phone_self_service_round_trip(monkeypatch, tmp_path):
    allow_role(monkeypatch, "admin")
    client = TestClient(web_app.app)

    stored = {"phone": None}

    monkeypatch.setattr(
        "roxx.core.auth.db.AdminDatabase.set_phone_number",
        lambda username, phone_number: stored.update(phone=phone_number) or True,
    )
    monkeypatch.setattr(
        "roxx.core.auth.db.AdminDatabase.get_phone_number",
        lambda username: stored["phone"],
    )
    monkeypatch.setattr(
        "roxx.web.app.AdminDatabase.set_phone_number",
        lambda username, phone_number: stored.update(phone=phone_number) or True,
    )
    monkeypatch.setattr(
        "roxx.web.app.AdminDatabase.get_phone_number",
        lambda username: stored["phone"],
    )
    monkeypatch.setattr(
        "roxx.core.auth.mfa_db.MFADatabase.get_mfa_settings",
        lambda username: None,
    )
    monkeypatch.setattr(
        "roxx.web.app.MFADatabase.get_mfa_settings",
        lambda username: None,
    )
    monkeypatch.setattr("roxx.web.app.SystemManager.get_config_dir", lambda: tmp_path)
    (tmp_path / "mfa_gateways.json").write_text(json.dumps({"sms": {"provider": "twilio"}}))

    response = client.put("/api/mfa/phone", json={"phone_number": "+33 6 12 34 56 78"})
    assert response.status_code == 200
    assert response.json()["phone_number"] == "+33612345678"

    status = client.get("/api/mfa/status")
    assert status.status_code == 200
    assert status.json()["sms_enabled"] is True
    assert status.json()["phone_number"] == "+33612345678"


def test_sms_login_otp_send(monkeypatch, tmp_path):
    auth = {"username": "alice", "status": "mfa_pending", "role": None}
    monkeypatch.setattr("roxx.core.auth.rbac.get_auth_context", lambda request: auth)
    monkeypatch.setattr(web_app, "get_auth_context", lambda request: auth)
    monkeypatch.setattr("roxx.web.app.SystemManager.get_config_dir", lambda: tmp_path)
    (tmp_path / "mfa_gateways.json").write_text(json.dumps({"sms": {"provider": "twilio"}}))

    captured = {}

    monkeypatch.setattr(
        "roxx.core.auth.db.AdminDatabase.get_phone_number",
        lambda username: "+33612345678",
    )
    monkeypatch.setattr(
        "roxx.web.app.AdminDatabase.get_phone_number",
        lambda username: "+33612345678",
    )

    async def fake_send_sms(phone_number, message, config):
        captured["phone_number"] = phone_number
        captured["message"] = message
        captured["config"] = config
        return True

    monkeypatch.setattr("roxx.web.app.SMSProvider.send_sms", fake_send_sms)

    client = TestClient(web_app.app)
    response = client.post("/auth/mfa/send-otp", json={"type": "sms"})

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert captured["phone_number"] == "+33612345678"
    assert "Your RoXX code is" in captured["message"]


def test_sensitive_pages_require_auth():
    client = TestClient(web_app.app)

    ssl_page = client.get("/config/ssl", follow_redirects=False)
    pki_page = client.get("/config/pki", follow_redirects=False)
    health = client.get("/health", headers={"accept": "application/json"})
    mfa_status = client.get("/api/mfa/status", headers={"accept": "application/json"})

    assert ssl_page.status_code == 401
    assert pki_page.status_code == 401
    assert health.status_code == 401
    assert mfa_status.status_code == 401
