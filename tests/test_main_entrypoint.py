"""Tests for the top-level RoXX command router."""

from __future__ import annotations

import sys
import types

import roxx.__main__ as roxx_main


def test_service_mode_forwards_arguments(monkeypatch):
    observed_argv = []

    def fake_service_main() -> None:
        observed_argv.extend(sys.argv)

    service_module = types.ModuleType("roxx.cli.service")
    service_module.main = fake_service_main
    monkeypatch.setitem(sys.modules, "roxx.cli.service", service_module)
    monkeypatch.setattr(
        sys,
        "argv",
        ["roxx", "service", "print-systemd", "--binary", "/opt/roxx/roxx-server"],
    )

    roxx_main.main()

    assert observed_argv == [
        "roxx service",
        "print-systemd",
        "--binary",
        "/opt/roxx/roxx-server",
    ]


def test_windows_service_mode_forwards_arguments(monkeypatch):
    observed_argv = []

    def fake_windows_service_main() -> None:
        observed_argv.extend(sys.argv)

    windows_service_module = types.ModuleType("roxx.cli.windows_service")
    windows_service_module.main = fake_windows_service_main
    monkeypatch.setitem(sys.modules, "roxx.cli.windows_service", windows_service_module)
    monkeypatch.setattr(sys, "argv", ["roxx", "windows-service", "install"])

    roxx_main.main()

    assert observed_argv == ["roxx windows-service", "install"]
