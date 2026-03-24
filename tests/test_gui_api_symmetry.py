from fastapi.testclient import TestClient
import asyncio
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


def test_pki_endpoints_expose_ca_and_certificates(monkeypatch, tmp_path):
    allow_role(monkeypatch, "superadmin")

    pki_dir = tmp_path / "pki"
    pki_dir.mkdir()
    (pki_dir / "ca.crt").write_text("ca")
    (pki_dir / "vpn-client.crt").write_text("cert")

    monkeypatch.setattr("roxx.core.security.pki.PKIManager.get_pki_dir", classmethod(lambda cls: pki_dir))

    client = TestClient(web_app.app)

    status = client.get("/api/pki/status")
    certs = client.get("/api/pki/certificates")
    ca_download = client.get("/api/pki/ca/download")
    cert_download = client.get("/api/pki/certificates/vpn-client/download")

    assert status.status_code == 200
    assert status.json()["exists"] is True
    assert status.json()["certificates"][0]["name"] == "vpn-client"
    assert certs.status_code == 200
    assert certs.json()["certificates"][0]["name"] == "vpn-client"
    assert ca_download.status_code == 200
    assert cert_download.status_code == 200


def test_radius_backend_update_uses_config_keyword(monkeypatch):
    allow_role(monkeypatch, "superadmin")

    captured = {}

    monkeypatch.setattr(
        "roxx.core.radius_backends.config_db.RadiusBackendDB.update_backend",
        lambda backend_id, **kwargs: captured.update({"backend_id": backend_id, **kwargs}) or (True, "ok"),
    )
    monkeypatch.setattr("roxx.core.radius_backends.manager.reload_manager", lambda: None)

    client = TestClient(web_app.app)
    response = client.put("/api/radius-backends/42", json={
        "name": "Updated Backend",
        "config": {"server": "ldap://dc.example.local"},
        "enabled": True,
        "priority": 50,
    })

    assert response.status_code == 200
    assert captured["backend_id"] == 42
    assert captured["config"] == {"server": "ldap://dc.example.local"}
    assert "config_dict" not in captured


def test_ssl_remove_keeps_business_error_as_400(monkeypatch):
    allow_role(monkeypatch, "superadmin")
    monkeypatch.setattr(
        "roxx.core.security.cert_manager.CertManager.remove_cert",
        lambda: (False, "No certificate configured"),
    )

    client = TestClient(web_app.app)
    response = client.post("/api/system/ssl/remove")

    assert response.status_code == 400
    assert response.json()["detail"] == "No certificate configured"


def test_nps_import_respects_selected_entries(monkeypatch):
    class FakeRequest:
        def __init__(self):
            self.headers = {"content-type": "application/json"}
            self.session = {
                "nps_import_buffer": {
                    "clients": [
                        {"name": "Client A", "address": "10.0.0.1", "shared_secret": "secret-a"},
                        {"name": "Client B", "address": "10.0.0.2", "shared_secret": "secret-b"},
                    ],
                    "remote_radius_servers": [
                        {"group": "HQ", "address": "192.168.1.10"},
                        {"group": "Branch", "address": "192.168.1.11"},
                    ],
                }
            }

        async def json(self):
            return {
                "selected_clients": ["Client A|10.0.0.1"],
                "selected_servers": ["Branch|192.168.1.11"],
            }

    added_clients = []
    created_backends = []

    monkeypatch.setattr(
        "roxx.core.radius_backends.config_db.RadiusBackendDB.add_client",
        lambda shortname, ipaddr, secret, description="": added_clients.append((shortname, ipaddr, secret, description)) or True,
    )
    monkeypatch.setattr(
        "roxx.core.radius_backends.config_db.RadiusBackendDB.create_backend",
        lambda backend_type, name, config, enabled=True, priority=100: created_backends.append(
            (backend_type, name, config, enabled, priority)
        ) or (True, "ok", 1),
    )

    response = asyncio.run(web_app.api_nps_import(FakeRequest()))

    assert response["success"] is True
    assert len(added_clients) == 1
    assert added_clients[0][1] == "10.0.0.1"
    assert len(created_backends) == 1
    assert created_backends[0][1].startswith("NPS_Branch_192_168_1_11")
