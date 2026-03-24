import asyncio
import base64

from starlette.requests import Request

from roxx.core.auth.rbac import Action, get_auth_context, require_action, require_role


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


def test_get_auth_context_migrates_legacy_cookie_and_resolves_role_server_side(monkeypatch):
    monkeypatch.setattr("roxx.core.auth.db.AdminDatabase.get_role", lambda username: "auditor")

    forged_cookie = base64.b64encode(b"alice:active:superadmin").decode("utf-8")
    request = make_request(cookie_value=forged_cookie)

    auth = get_auth_context(request)

    assert auth == {"username": "alice", "status": "active", "role": "auditor"}
    assert request.session["auth"]["role"] == "auditor"


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
