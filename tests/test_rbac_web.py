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


def test_websocket_accepts_valid_signed_session(monkeypatch):
    monkeypatch.setattr(AdminDatabase, "get_role", lambda username: "auditor")
    session = base64.b64encode(json.dumps({"auth": {
        "username": "alice", "status": "active", "role": "superadmin"
    }}).encode("utf-8"))
    signed = TimestampSigner(web_app.SECRET_KEY).sign(session).decode("utf-8")
    client = TestClient(web_app.app)
    with client.websocket_connect("/ws/logs", headers={"Cookie": f"roxx_session={signed}"}) as websocket:
        assert "Connected" in websocket.receive_text()


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
