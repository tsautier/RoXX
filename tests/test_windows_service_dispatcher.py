"""Windows Service Control Manager entry point checks."""

from __future__ import annotations

import os
import sys

import pytest

from roxx.cli import windows_service


@pytest.mark.skipif(os.name != "nt", reason="pywin32 service registration is Windows-only")
def test_frozen_service_uses_single_executable_dispatcher(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "argv", ["roxx windows-service", "run"])
    monkeypatch.setattr(windows_service.servicemanager, "Initialize", lambda: calls.append("initialize"))
    monkeypatch.setattr(
        windows_service.servicemanager,
        "PrepareToHostSingle",
        lambda service: calls.append(service),
    )
    monkeypatch.setattr(
        windows_service.servicemanager,
        "StartServiceCtrlDispatcher",
        lambda: calls.append("dispatch"),
    )

    windows_service.main()

    assert windows_service.RoXXWindowsService._exe_args_ == "windows-service run"
    assert calls == ["initialize", windows_service.RoXXWindowsService, "dispatch"]
