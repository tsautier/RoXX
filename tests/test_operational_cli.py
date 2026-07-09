"""Tests for operational commands exposed by the unified launcher."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from roxx.cli import audit
from roxx.setup.bootstrap import bootstrap_production


def test_audit_export_writes_jsonl(monkeypatch, tmp_path):
    output = tmp_path / "audit.jsonl"
    records = [{"id": 1, "action": "LOGIN", "details": {"success": True}}]
    monkeypatch.setattr(audit.AuditDatabase, "get_logs", lambda limit: records)
    monkeypatch.setattr(sys, "argv", ["roxx audit", "export", "--output", str(output)])

    audit.main()

    assert json.loads(output.read_text(encoding="utf-8")) == records[0]


def test_non_interactive_bootstrap_writes_production_environment(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    log_dir = tmp_path / "logs"
    cert = config_dir / "certs" / "server.crt"
    key = config_dir / "certs" / "server.key"
    monkeypatch.setenv("ROXX_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("ROXX_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ROXX_LOG_DIR", str(log_dir))
    monkeypatch.delenv("ROXX_SECRET_KEY", raising=False)
    monkeypatch.setattr("roxx.setup.bootstrap.CertManager.get_cert_paths", lambda: (cert, key))

    def generate_certificate(hostname: str):
        cert.parent.mkdir(parents=True, exist_ok=True)
        cert.write_text(hostname, encoding="utf-8")
        key.write_text("private", encoding="utf-8")
        return True, "generated"

    monkeypatch.setattr(
        "roxx.setup.bootstrap.CertManager.generate_self_signed_cert",
        generate_certificate,
    )

    result = bootstrap_production("roxx.example.com", Path("roxx"), tmp_path)

    environment = Path(result.environment_file).read_text(encoding="utf-8")
    summary = (config_dir / "bootstrap-result.json").read_text(encoding="utf-8")
    assert "ROXX_SECURITY_PROFILE=production" in environment
    assert "ROXX_SECRET_KEY=" in environment
    assert "ROXX_SECRET_KEY" not in summary
    assert result.certificate_generated is True
