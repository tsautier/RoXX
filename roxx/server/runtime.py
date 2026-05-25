"""Production server runtime for RoXX web deployments."""

from __future__ import annotations

import os
import ssl
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import uvicorn

from roxx.core.security.cert_manager import CertManager
from roxx.utils.system import SystemManager


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


@dataclass
class ServerRuntimeConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    app_import: str = "roxx.web.app:app"
    ssl_required: bool = True
    auto_generate_cert: bool = True
    access_log: bool = True
    proxy_headers: bool = True
    timeout_keep_alive: int = 30
    backlog: int = 2048
    root_path: str = ""
    limit_concurrency: Optional[int] = None
    client_cert_mode: str = "optional"
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    ssl_ca_certs: Optional[str] = None

    @classmethod
    def from_env(cls) -> "ServerRuntimeConfig":
        return cls(
            host=os.getenv("ROXX_HOST", "0.0.0.0"),
            port=_env_int("ROXX_PORT", 8000),
            log_level=os.getenv("ROXX_LOG_LEVEL", "info").lower(),
            app_import=os.getenv("ROXX_APP_IMPORT", "roxx.web.app:app"),
            ssl_required=_env_flag("ROXX_SSL_REQUIRED", True),
            auto_generate_cert=_env_flag("ROXX_AUTO_GENERATE_CERT", True),
            access_log=_env_flag("ROXX_ACCESS_LOG", True),
            proxy_headers=_env_flag("ROXX_PROXY_HEADERS", True),
            timeout_keep_alive=_env_int("ROXX_TIMEOUT_KEEP_ALIVE", 30),
            backlog=_env_int("ROXX_BACKLOG", 2048),
            root_path=os.getenv("ROXX_ROOT_PATH", ""),
            limit_concurrency=(
                _env_int("ROXX_LIMIT_CONCURRENCY", 0) or None
                if os.getenv("ROXX_LIMIT_CONCURRENCY") is not None
                else None
            ),
            client_cert_mode=os.getenv("ROXX_CLIENT_CERT_MODE", "optional").lower(),
            ssl_certfile=os.getenv("ROXX_SSL_CERTFILE"),
            ssl_keyfile=os.getenv("ROXX_SSL_KEYFILE"),
            ssl_ca_certs=os.getenv("ROXX_SSL_CA_CERTS"),
        )


def _resolve_ssl_paths(config: ServerRuntimeConfig) -> tuple[Optional[Path], Optional[Path], Optional[Path]]:
    cert_path = Path(config.ssl_certfile) if config.ssl_certfile else None
    key_path = Path(config.ssl_keyfile) if config.ssl_keyfile else None
    ca_path = Path(config.ssl_ca_certs) if config.ssl_ca_certs else None

    if cert_path is None or key_path is None:
        default_cert, default_key = CertManager.get_cert_paths()
        cert_path = cert_path or default_cert
        key_path = key_path or default_key

    if ca_path is None:
        ca_path = CertManager.get_ca_paths()

    return cert_path, key_path, ca_path


def _ensure_ssl_material(config: ServerRuntimeConfig) -> tuple[Optional[Path], Optional[Path], Optional[Path]]:
    cert_path, key_path, ca_path = _resolve_ssl_paths(config)
    ssl_enabled = bool(cert_path and key_path and cert_path.exists() and key_path.exists())

    if not ssl_enabled and config.auto_generate_cert:
        SystemManager.ensure_directories()
        success, message = CertManager.generate_self_signed_cert()
        if not success:
            if config.ssl_required:
                raise RuntimeError(f"Failed to generate SSL certificate: {message}")
            return cert_path, key_path, ca_path
        cert_path, key_path, ca_path = _resolve_ssl_paths(config)
        ssl_enabled = cert_path.exists() and key_path.exists()

    if config.ssl_required and not ssl_enabled:
        raise RuntimeError("SSL is required but no usable certificate/key pair is available")

    return cert_path, key_path, ca_path


def build_uvicorn_config(config: Optional[ServerRuntimeConfig] = None) -> uvicorn.Config:
    config = config or ServerRuntimeConfig.from_env()
    cert_path, key_path, ca_path = _ensure_ssl_material(config)

    kwargs = {
        "app": config.app_import,
        "host": config.host,
        "port": config.port,
        "log_level": config.log_level,
        "access_log": config.access_log,
        "proxy_headers": config.proxy_headers,
        "timeout_keep_alive": config.timeout_keep_alive,
        "backlog": config.backlog,
        "root_path": config.root_path,
    }

    if config.limit_concurrency is not None:
        kwargs["limit_concurrency"] = config.limit_concurrency

    if cert_path and key_path and cert_path.exists() and key_path.exists():
        kwargs["ssl_certfile"] = str(cert_path)
        kwargs["ssl_keyfile"] = str(key_path)

        if ca_path and ca_path.exists():
            kwargs["ssl_ca_certs"] = str(ca_path)
            if config.client_cert_mode == "required":
                kwargs["ssl_cert_reqs"] = ssl.CERT_REQUIRED
            elif config.client_cert_mode == "optional":
                kwargs["ssl_cert_reqs"] = ssl.CERT_OPTIONAL

    return uvicorn.Config(**kwargs)


def create_server(config: Optional[ServerRuntimeConfig] = None) -> uvicorn.Server:
    return uvicorn.Server(build_uvicorn_config(config))


def run_web_server(
    config: Optional[ServerRuntimeConfig] = None,
    stop_event: Optional[threading.Event] = None,
) -> int:
    server = create_server(config)

    if stop_event is not None:
        def _watch_stop() -> None:
            stop_event.wait()
            server.should_exit = True

        watcher = threading.Thread(target=_watch_stop, daemon=True, name="roxx-server-stop")
        watcher.start()

    server.run()
    return 0 if not server.started or server.should_exit else 1

