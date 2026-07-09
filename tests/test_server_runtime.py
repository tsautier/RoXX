from pathlib import Path

from roxx.cli.service import build_arg_parser, render_systemd_unit
from roxx.server.runtime import ServerRuntimeConfig, build_uvicorn_config


def test_server_runtime_config_from_env(monkeypatch):
    monkeypatch.setenv("ROXX_HOST", "127.0.0.1")
    monkeypatch.setenv("ROXX_PORT", "9443")
    monkeypatch.setenv("ROXX_LOG_LEVEL", "warning")
    monkeypatch.setenv("ROXX_SSL_REQUIRED", "true")
    monkeypatch.setenv("ROXX_AUTO_GENERATE_CERT", "false")
    monkeypatch.setenv("ROXX_TIMEOUT_KEEP_ALIVE", "45")
    monkeypatch.setenv("ROXX_BACKLOG", "1024")
    monkeypatch.setenv("ROXX_LIMIT_CONCURRENCY", "200")
    monkeypatch.setenv("ROXX_CLIENT_CERT_MODE", "required")

    config = ServerRuntimeConfig.from_env()

    assert config.host == "127.0.0.1"
    assert config.port == 9443
    assert config.log_level == "warning"
    assert config.ssl_required is True
    assert config.auto_generate_cert is False
    assert config.timeout_keep_alive == 45
    assert config.backlog == 1024
    assert config.limit_concurrency == 200
    assert config.client_cert_mode == "required"


def test_build_uvicorn_config_uses_explicit_cert_paths(monkeypatch, tmp_path):
    cert = tmp_path / "server.crt"
    key = tmp_path / "server.key"
    ca = tmp_path / "ca.crt"
    cert.write_text("cert")
    key.write_text("key")
    ca.write_text("ca")

    config = ServerRuntimeConfig(
        ssl_required=True,
        auto_generate_cert=False,
        ssl_certfile=str(cert),
        ssl_keyfile=str(key),
        ssl_ca_certs=str(ca),
        client_cert_mode="required",
    )

    uvicorn_config = build_uvicorn_config(config)

    assert uvicorn_config.ssl_certfile == str(cert)
    assert uvicorn_config.ssl_keyfile == str(key)
    assert uvicorn_config.ssl_ca_certs == str(ca)
    assert uvicorn_config.ssl_cert_reqs == 2


def test_render_systemd_unit_contains_restart_policy():
    unit = render_systemd_unit(
        binary_path=Path("/opt/roxx/roxx"),
        user="roxx",
        group="roxx",
        working_directory=Path("/opt/roxx"),
        config_dir=Path("/etc/roxx"),
        data_dir=Path("/var/lib/roxx"),
        log_dir=Path("/var/log/roxx"),
    )

    assert "ExecStart=/opt/roxx/roxx server" in unit
    assert "Restart=always" in unit
    assert "User=roxx" in unit


def test_systemd_helper_defaults_to_unified_roxx_launcher():
    args = build_arg_parser().parse_args(["print-systemd"])

    assert args.binary == "roxx"
