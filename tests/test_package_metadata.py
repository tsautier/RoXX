"""Tests for the public package command layout."""

from __future__ import annotations

import tomllib
from pathlib import Path


def test_package_exposes_only_unified_roxx_command():
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["scripts"] == {"roxx": "roxx.__main__:main"}
