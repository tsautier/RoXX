"""Security tests for first-run administrator provisioning."""

from __future__ import annotations

import bcrypt

from roxx.core.auth.db import AdminDatabase
from roxx.core.auth.manager import AuthManager


def _configure_database(monkeypatch, tmp_path):
    import roxx.core.auth.db as db_module

    database = tmp_path / "roxx.db"
    monkeypatch.setattr(db_module, "DB_PATH", database)
    monkeypatch.delenv("ROXX_BOOTSTRAP_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ROXX_BOOTSTRAP_ADMIN_PASSWORD", raising=False)
    return database


def _password_from_credentials_file() -> str:
    content = AuthManager.get_initial_credentials_path().read_text(encoding="utf-8")
    return next(
        line.removeprefix("Password: ")
        for line in content.splitlines()
        if line.startswith("Password: ")
    )


def test_first_run_generates_unique_admin_password(monkeypatch, tmp_path):
    _configure_database(monkeypatch, tmp_path)

    AuthManager.init()

    password = _password_from_credentials_file()
    success, user = AuthManager.verify_credentials("admin", password)
    assert success is True
    assert user["must_change_password"] == 1
    assert AuthManager.verify_credentials("admin", "admin")[0] is False
    assert len(password) >= 32


def test_supplied_bootstrap_password_is_not_written_to_disk(monkeypatch, tmp_path):
    _configure_database(monkeypatch, tmp_path)
    password = "Supplied-Admin-Password-2026!"
    monkeypatch.setenv("ROXX_BOOTSTRAP_ADMIN_PASSWORD", password)

    AuthManager.init()

    assert AuthManager.verify_credentials("admin", password)[0] is True
    assert AuthManager.get_initial_credentials_path().exists() is False


def test_password_rotation_removes_initial_credentials(monkeypatch, tmp_path):
    _configure_database(monkeypatch, tmp_path)
    AuthManager.init()
    initial_password = _password_from_credentials_file()

    AuthManager.change_password("admin", "Replacement-Admin-Password-2026!")

    assert AuthManager.get_initial_credentials_path().exists() is False
    assert AuthManager.verify_credentials("admin", initial_password)[0] is False
    assert AuthManager.verify_credentials("admin", "Replacement-Admin-Password-2026!")[0] is True


def test_legacy_admin_password_is_rotated(monkeypatch, tmp_path):
    _configure_database(monkeypatch, tmp_path)
    AdminDatabase.init_db()
    legacy_hash = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode("utf-8")
    with AdminDatabase.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO admins (username, password_hash, must_change_password, role)
            VALUES ('admin', ?, 1, 'superadmin')
            """,
            (legacy_hash,),
        )

    AuthManager.init()

    replacement = _password_from_credentials_file()
    assert AuthManager.verify_credentials("admin", "admin")[0] is False
    assert AuthManager.verify_credentials("admin", replacement)[0] is True


def test_saml_account_cannot_use_password_login(monkeypatch, tmp_path):
    _configure_database(monkeypatch, tmp_path)
    AdminDatabase.init_db()
    created, _ = AuthManager.create_admin("saml-user", None, auth_source="saml")

    assert created is True
    assert AuthManager.get_auth_source("saml-user") == "saml"
    assert AuthManager.verify_credentials("saml-user", "any-password")[0] is False


def test_unknown_authentication_source_is_rejected(monkeypatch, tmp_path):
    _configure_database(monkeypatch, tmp_path)
    AdminDatabase.init_db()
    with AdminDatabase.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO admins (username, password_hash, auth_source, role)
            VALUES ('invalid-user', NULL, 'invalid', 'admin')
            """
        )

    assert AuthManager.verify_credentials("invalid-user", "any-password")[0] is False
