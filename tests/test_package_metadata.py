"""Tests for the public package command layout."""

from __future__ import annotations

import tomllib
from pathlib import Path

import roxx


def test_package_exposes_only_unified_roxx_command():
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["scripts"] == {"roxx": "roxx.__main__:main"}


def test_release_version_is_consistent():
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    version = metadata["project"]["version"]

    assert Path("version.txt").read_text(encoding="utf-8").strip() == version
    assert roxx.__version__ == version
    assert f"# RoXX (v{version})" in Path("README.md").read_text(encoding="utf-8")
    assert f"## [{version}]" in Path("CHANGELOG.md").read_text(encoding="utf-8")
    assert f'LABEL version="{version}"' in Path("Dockerfile").read_text(encoding="utf-8")
    assert f"roxx v{version}" in Path("roxx/web/templates/base.html").read_text(
        encoding="utf-8"
    )
    assert Path(f"RELEASE_NOTES_v{version}.md").is_file()
