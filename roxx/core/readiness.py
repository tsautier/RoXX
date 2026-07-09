"""Non-sensitive readiness checks for local and optional dependencies."""

from __future__ import annotations

import os
import re
import socket
import sqlite3
from pathlib import Path

from roxx.core.auth.db import AdminDatabase
from roxx.utils.system import SystemManager


def _check_writable_directory(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".roxx_readyz"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink(missing_ok=True)
    return True


def _check_database() -> bool:
    database_path = SystemManager.get_config_dir() / AdminDatabase.get_db_path().name
    with sqlite3.connect(database_path, timeout=1) as connection:
        connection.execute("SELECT 1").fetchone()
    return True


def _optional_tcp_checks() -> dict[str, bool]:
    """Check named host:port targets without returning addresses or credentials."""
    checks: dict[str, bool] = {}
    raw_targets = os.getenv("ROXX_READINESS_TCP_TARGETS", "")
    for raw_target in filter(None, (item.strip() for item in raw_targets.split(","))):
        safe_name = ""
        try:
            name, address = raw_target.split("=", 1)
            host, port_text = address.rsplit(":", 1)
            safe_name = re.sub(r"[^a-z0-9_]+", "_", name.strip().lower()).strip("_")
            if not safe_name:
                continue
            with socket.create_connection((host.strip(), int(port_text)), timeout=0.75):
                checks[f"backend_{safe_name}"] = True
        except (OSError, ValueError):
            if safe_name:
                checks[f"backend_{safe_name}"] = False
    return checks


def collect_readiness_checks() -> dict[str, bool]:
    checks: dict[str, bool] = {}
    local_checks = {
        "config_dir": lambda: _check_writable_directory(SystemManager.get_config_dir()),
        "data_dir": lambda: _check_writable_directory(SystemManager.get_data_dir()),
        "log_dir": lambda: _check_writable_directory(SystemManager.get_log_dir()),
        "database": _check_database,
    }
    for name, check in local_checks.items():
        try:
            checks[name] = check()
        except (OSError, sqlite3.Error):
            checks[name] = False
    checks.update(_optional_tcp_checks())
    return checks
