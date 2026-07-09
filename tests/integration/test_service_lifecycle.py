"""Exercise repeated server start, probe, termination, and restart."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _wait_for_probe(port: int, process: subprocess.Popen, stderr_path: Path) -> dict:
    deadline = time.monotonic() + 20
    url = f"http://127.0.0.1:{port}/livez"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(stderr_path.read_text(encoding="utf-8", errors="replace"))
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                return json.load(response)
        except OSError:
            time.sleep(0.25)
    raise AssertionError(f"Server did not become live; stderr={stderr_path.read_text(errors='replace')}")


def _run_once(tmp_path: Path, attempt: int) -> None:
    port = _free_port()
    stdout_path = tmp_path / f"server-{attempt}.stdout.log"
    stderr_path = tmp_path / f"server-{attempt}.stderr.log"
    environment = os.environ.copy()
    environment.update(
        {
            "ROXX_HOST": "127.0.0.1",
            "ROXX_PORT": str(port),
            "ROXX_SSL_REQUIRED": "false",
            "ROXX_AUTO_GENERATE_CERT": "false",
            "ROXX_CONFIG_DIR": str(tmp_path / "config"),
            "ROXX_DATA_DIR": str(tmp_path / "data"),
            "ROXX_LOG_DIR": str(tmp_path / "logs"),
        }
    )
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr:
        process = subprocess.Popen(
            [sys.executable, "-m", "roxx", "server"],
            env=environment,
            stdout=stdout,
            stderr=stderr,
            text=True,
        )
        try:
            assert _wait_for_probe(port, process, stderr_path) == {
                "status": "ok",
                "service": "roxx-web",
            }
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    assert "Application startup complete" in stderr_path.read_text(
        encoding="utf-8", errors="replace"
    )


def test_server_survives_clean_restart(tmp_path):
    _run_once(tmp_path, 1)
    _run_once(tmp_path, 2)
