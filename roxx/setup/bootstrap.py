"""Non-interactive production bootstrap for repeatable RoXX deployments."""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path

from roxx.cli.service import install_systemd_unit, render_systemd_unit
from roxx.core.security.cert_manager import CertManager
from roxx.utils.system import SystemManager


@dataclass(frozen=True)
class BootstrapResult:
    config_dir: str
    data_dir: str
    log_dir: str
    environment_file: str
    certificate_generated: bool
    service_installed: bool


def bootstrap_production(
    hostname: str,
    binary_path: Path,
    working_directory: Path,
    user: str = "roxx",
    group: str = "roxx",
    install_service: bool = False,
    unit_path: Path = Path("/etc/systemd/system/roxx.service"),
) -> BootstrapResult:
    config_dir = SystemManager.get_config_dir()
    data_dir = SystemManager.get_data_dir()
    log_dir = SystemManager.get_log_dir()
    for directory in (config_dir, data_dir, log_dir):
        directory.mkdir(parents=True, exist_ok=True)

    environment_file = config_dir / "roxx.env"
    secret_key = os.getenv("ROXX_SECRET_KEY") or secrets.token_urlsafe(48)
    environment_file.write_text(
        "\n".join(
            [
                "ROXX_SECURITY_PROFILE=production",
                f"ROXX_SECRET_KEY={secret_key}",
                "ROXX_SSL_REQUIRED=true",
                "ROXX_SECURE_COOKIES=true",
                "ROXX_HSTS=true",
                f"ROXX_CONFIG_DIR={config_dir}",
                f"ROXX_DATA_DIR={data_dir}",
                f"ROXX_LOG_DIR={log_dir}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    if os.name != "nt":
        environment_file.chmod(0o600)

    cert_path, key_path = CertManager.get_cert_paths()
    certificate_generated = cert_path.exists() and key_path.exists()
    if not certificate_generated:
        certificate_generated, message = CertManager.generate_self_signed_cert(hostname)
        if not certificate_generated:
            raise RuntimeError(message)

    if install_service:
        unit = render_systemd_unit(
            binary_path=binary_path,
            user=user,
            group=group,
            working_directory=working_directory,
            config_dir=config_dir,
            data_dir=data_dir,
            log_dir=log_dir,
        )
        install_systemd_unit(unit_path, unit)

    result = BootstrapResult(
        config_dir=str(config_dir),
        data_dir=str(data_dir),
        log_dir=str(log_dir),
        environment_file=str(environment_file),
        certificate_generated=certificate_generated,
        service_installed=install_service,
    )
    (config_dir / "bootstrap-result.json").write_text(
        json.dumps(asdict(result), indent=2),
        encoding="utf-8",
    )
    return result
