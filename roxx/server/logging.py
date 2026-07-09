"""Logging configuration shared by interactive and supervised server runs."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from roxx.utils.system import SystemManager


def configure_service_logging(level: str = "info", log_dir: Path | None = None) -> Path:
    """Configure console and rotating-file logs and return the active log file."""
    directory = log_dir or SystemManager.get_log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    log_file = directory / "roxx-server.log"
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    for handler in list(root.handlers):
        if getattr(handler, "_roxx_managed", False):
            root.removeHandler(handler)
            handler.close()

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console._roxx_managed = True  # type: ignore[attr-defined]

    rotating = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    rotating.setFormatter(formatter)
    rotating._roxx_managed = True  # type: ignore[attr-defined]

    root.addHandler(console)
    root.addHandler(rotating)
    return log_file
