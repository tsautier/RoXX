"""Runtime directory tests for service-owned SQLite databases."""

from __future__ import annotations


def test_secondary_databases_follow_config_directory(monkeypatch, tmp_path):
    from roxx.core.auth import api_tokens, mfa_db, webauthn_db
    from roxx.core.radius_backends import config_db

    monkeypatch.setenv("ROXX_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(api_tokens, "DB_PATH", api_tokens._INITIAL_DB_PATH)
    monkeypatch.setattr(mfa_db, "DB_PATH", mfa_db._INITIAL_DB_PATH)
    monkeypatch.setattr(webauthn_db, "DB_PATH", webauthn_db._INITIAL_DB_PATH)
    monkeypatch.setattr(config_db, "DB_PATH", config_db._INITIAL_DB_PATH)

    assert api_tokens._get_db_path() == tmp_path / "api_tokens.db"
    assert mfa_db._get_db_path() == tmp_path / "mfa.db"
    assert webauthn_db._get_db_path() == tmp_path / "webauthn.db"
    assert config_db._get_db_path() == tmp_path / "radius_backends.db"


def test_explicit_test_database_paths_remain_supported(monkeypatch, tmp_path):
    from roxx.core.auth import api_tokens
    from roxx.core.radius_backends import config_db

    api_database = tmp_path / "api-test.db"
    radius_database = tmp_path / "radius-test.db"
    monkeypatch.setattr(api_tokens, "DB_PATH", api_database)
    monkeypatch.setattr(config_db, "DB_PATH", radius_database)

    assert api_tokens._get_db_path() == api_database
    assert config_db._get_db_path() == radius_database
