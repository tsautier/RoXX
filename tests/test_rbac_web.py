import asyncio
import base64
import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from starlette.websockets import WebSocketDisconnect
from starlette.requests import Request

import roxx.web.app as web_app
from roxx.core.auth.db import AdminDatabase
from roxx.core.auth.rbac import Action, get_auth_context, require_action, require_role, set_auth_context
from roxx.core.security.origin import is_trusted_origin


def make_request(*, cookie_value=None, session_auth=None):
    headers = []
    if cookie_value is not None:
        headers.append((b"cookie", f"session={cookie_value}".encode("utf-8")))

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "session": {},
    }
    if session_auth is not None:
        scope["session"]["auth"] = session_auth
    return Request(scope)


def test_get_auth_context_rejects_legacy_unsigned_cookie(monkeypatch):
    monkeypatch.setattr("roxx.core.auth.db.AdminDatabase.get_role", lambda username: "auditor")

    forged_cookie = base64.b64encode(b"alice:active:superadmin").decode("utf-8")
    request = make_request(cookie_value=forged_cookie)

    auth = get_auth_context(request)

    assert auth is None
    assert request.session == {}


def test_legacy_cookie_cannot_access_protected_api():
    forged_cookie = base64.b64encode(b"admin:active:superadmin").decode("utf-8")
    response = TestClient(web_app.app).get("/api/system/info", cookies={"session": forged_cookie})
    assert response.status_code == 401


def test_missing_or_invalid_database_role_invalidates_signed_session(monkeypatch):
    request = make_request(session_auth={"username": "alice", "status": "active", "role": "superadmin"})
    for role in (None, "", "invalid"):
        monkeypatch.setattr(AdminDatabase, "get_role", lambda username: role)
        assert get_auth_context(request) is None
        with pytest.raises(HTTPException) as error:
            asyncio.run(require_action(Action.VIEW_LOGS)(request))
        assert error.value.status_code == 401
        with pytest.raises(HTTPException) as error:
            asyncio.run(require_role("admin")(request))
        assert error.value.status_code == 401
        with pytest.raises(HTTPException) as error:
            set_auth_context(request, "alice", "active")
        assert error.value.status_code == 403


def test_signed_session_uses_current_database_role(monkeypatch):
    monkeypatch.setattr(AdminDatabase, "get_role", lambda username: "auditor")
    request = make_request(session_auth={"username": "alice", "status": "active", "role": "superadmin"})
    assert get_auth_context(request)["role"] == "auditor"


def test_database_does_not_assign_admin_to_missing_or_unset_role(monkeypatch, tmp_path):
    monkeypatch.setattr(AdminDatabase, "get_db_path", lambda: tmp_path / "admins.db")
    AdminDatabase.init_db()
    assert AdminDatabase.get_role("missing") is None
    with AdminDatabase.get_connection() as connection:
        connection.execute(
            "INSERT INTO admins (username, role) VALUES (?, ?)", ("alice", None)
        )
    assert AdminDatabase.get_role("alice") is None


def test_websocket_rejects_basic_auth_without_signed_session():
    credentials = base64.b64encode(b"admin:admin").decode("ascii")
    client = TestClient(web_app.app)
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/ws/logs", headers={"Authorization": f"Basic {credentials}"}):
            pass
    assert error.value.code == 1008


def signed_session_cookie():
    session = base64.b64encode(json.dumps({"auth": {
        "username": "alice", "status": "active", "role": "superadmin"
    }}).encode("utf-8"))
    return TimestampSigner(web_app.SECRET_KEY).sign(session).decode("utf-8")


def test_websocket_accepts_valid_signed_session(monkeypatch):
    monkeypatch.setattr(AdminDatabase, "get_role", lambda username: "auditor")
    client = TestClient(web_app.app)
    headers = {"Cookie": f"roxx_session={signed_session_cookie()}", "Origin": "http://testserver"}
    with client.websocket_connect("/ws/logs", headers=headers) as websocket:
        assert "Connected" in websocket.receive_text()


@pytest.mark.parametrize("origin", [None, "https://attacker.example", "null", "http://testserver.evil"])
def test_websocket_rejects_untrusted_origin_with_valid_session(monkeypatch, origin):
    monkeypatch.setattr(AdminDatabase, "get_role", lambda username: "auditor")
    headers = {"Cookie": f"roxx_session={signed_session_cookie()}"}
    if origin is not None:
        headers["Origin"] = origin
    with pytest.raises(WebSocketDisconnect) as error:
        with TestClient(web_app.app).websocket_connect("/ws/logs", headers=headers):
            pass
    assert error.value.code == 1008


def test_websocket_rejects_cross_site_fetch_metadata(monkeypatch):
    monkeypatch.setattr(AdminDatabase, "get_role", lambda username: "auditor")
    headers = {
        "Cookie": f"roxx_session={signed_session_cookie()}",
        "Origin": "http://testserver",
        "Sec-Fetch-Site": "cross-site",
    }
    with pytest.raises(WebSocketDisconnect) as error:
        with TestClient(web_app.app).websocket_connect("/ws/logs", headers=headers):
            pass
    assert error.value.code == 1008


def test_cookie_authenticated_mutation_requires_same_origin(monkeypatch):
    monkeypatch.setattr(AdminDatabase, "get_role", lambda username: "admin")
    monkeypatch.setattr(web_app.SystemManager, "add_radius_user", lambda username, password: False)
    client = TestClient(web_app.app)
    client.cookies.set("roxx_session", signed_session_cookie())
    for headers in ({}, {"Origin": "https://attacker.example"}, {"Origin": "null"},
                    {"Origin": "http://testserver", "Sec-Fetch-Site": "cross-site"}):
        response = client.post("/api/users", json={"username": "test", "password": "test"}, headers=headers)
        assert response.status_code == 403
    response = client.post("/api/users", json={"username": "test", "password": "test"},
                           headers={"Origin": "http://testserver"})
    assert response.status_code == 200
    assert response.json() == {"success": False}
    response = client.post("/api/users", json={"username": "test", "password": "test"},
                           headers={"Referer": "http://testserver/users"})
    assert response.status_code == 200
    response = client.post("/api/users", json={"username": "test", "password": "test"},
                           headers={"Referer": "https://attacker.example/form"})
    assert response.status_code == 403


def test_logout_requires_post_and_same_origin():
    client = TestClient(web_app.app)
    client.cookies.set("roxx_session", signed_session_cookie())
    assert client.get("/logout").status_code == 405
    assert client.post("/logout", headers={"Origin": "https://attacker.example"}).status_code == 403
    assert client.post("/logout", headers={"Origin": "http://testserver"},
                       follow_redirects=False).status_code == 307


def test_radius_user_list_does_not_disclose_password(monkeypatch, tmp_path):
    monkeypatch.setattr(AdminDatabase, "get_role", lambda username: "admin")
    monkeypatch.setattr(web_app.SystemManager, "get_config_dir", lambda: tmp_path)
    (tmp_path / "users.conf").write_text('alice Cleartext-Password := "top-secret"\n')
    client = TestClient(web_app.app)
    client.cookies.set("roxx_session", signed_session_cookie())
    response = client.get("/api/users")
    assert response.status_code == 200
    assert response.json() == [{"username": "alice", "attribute": "Cleartext-Password", "op": ":="}]
    assert "top-secret" not in response.text


def test_configured_proxy_origin_is_accepted(monkeypatch):
    monkeypatch.setenv("ROXX_ALLOWED_ORIGINS", "https://roxx.example")
    monkeypatch.setattr(AdminDatabase, "get_role", lambda username: "admin")
    monkeypatch.setattr(web_app.SystemManager, "add_radius_user", lambda username, password: False)
    client = TestClient(web_app.app)
    client.cookies.set("roxx_session", signed_session_cookie())
    response = client.post("/api/users", json={"username": "test", "password": "test"},
                           headers={"Origin": "https://roxx.example"})
    assert response.status_code == 200
    response = client.post("/api/users", json={"username": "test", "password": "test"},
                           headers={"Origin": "http://testserver"})
    assert response.status_code == 403


@pytest.mark.parametrize("origin", ["null", "https://roxx.example.evil", "https://roxx.example/path",
                                     "https://user@roxx.example", "https://[invalid"])
def test_origin_allowlist_rejects_ambiguous_values(monkeypatch, origin):
    monkeypatch.setenv("ROXX_ALLOWED_ORIGINS", "https://roxx.example")
    from starlette.datastructures import URL
    assert not is_trusted_origin(origin, URL("http://testserver/api/users"))


def test_require_action_denies_auditor_for_mutation(monkeypatch):
    monkeypatch.setattr("roxx.core.auth.db.AdminDatabase.get_role", lambda username: "auditor")
    request = make_request(session_auth={"username": "alice", "status": "active", "role": "superadmin"})

    dependency = require_action(Action.MANAGE_API_TOKENS)

    try:
        asyncio.run(dependency(request))
        assert False, "Expected permission denial"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403


def test_require_action_allows_superadmin(monkeypatch):
    monkeypatch.setattr("roxx.core.auth.db.AdminDatabase.get_role", lambda username: "superadmin")
    request = make_request(session_auth={"username": "alice", "status": "active", "role": "auditor"})

    dependency = require_action(Action.MANAGE_API_TOKENS)
    username = asyncio.run(dependency(request))

    assert username == "alice"


def test_require_role_enforces_superadmin(monkeypatch):
    monkeypatch.setattr("roxx.core.auth.db.AdminDatabase.get_role", lambda username: "admin")
    request = make_request(session_auth={"username": "alice", "status": "active", "role": "admin"})

    dependency = require_role("superadmin")

    try:
        asyncio.run(dependency(request))
        assert False, "Expected role denial"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403


def test_require_action_denies_admin_role_management(monkeypatch):
    monkeypatch.setattr("roxx.core.auth.db.AdminDatabase.get_role", lambda username: "admin")
    request = make_request(session_auth={"username": "alice", "status": "active", "role": "superadmin"})

    dependency = require_action(Action.CHANGE_ROLES)

    try:
        asyncio.run(dependency(request))
        assert False, "Expected permission denial"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403


def test_require_action_allows_superadmin_role_management(monkeypatch):
    monkeypatch.setattr("roxx.core.auth.db.AdminDatabase.get_role", lambda username: "superadmin")
    request = make_request(session_auth={"username": "alice", "status": "active", "role": "auditor"})

    dependency = require_action(Action.CHANGE_ROLES)
    username = asyncio.run(dependency(request))

    assert username == "alice"
