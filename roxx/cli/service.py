"""Service helper commands for long-running RoXX deployments."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
from pathlib import Path


SYSTEMD_TEMPLATE = """[Unit]
Description=RoXX Web Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
Group={group}
WorkingDirectory={working_directory}
Environment=ROXX_CONFIG_DIR={config_dir}
Environment=ROXX_DATA_DIR={data_dir}
Environment=ROXX_LOG_DIR={log_dir}
EnvironmentFile=-{config_dir}/roxx.env
ExecStart={exec_start}
Restart=always
RestartSec=5
TimeoutStopSec=30
KillSignal=SIGTERM
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={config_dir} {data_dir} {log_dir}

[Install]
WantedBy=multi-user.target
"""


def _systemd_path(path: Path) -> str:
    """Render service paths with POSIX separators, even when generated on Windows."""
    return path.as_posix()


def render_systemd_unit(
    binary_path: Path,
    user: str,
    group: str,
    working_directory: Path,
    config_dir: Path,
    data_dir: Path,
    log_dir: Path,
) -> str:
    return SYSTEMD_TEMPLATE.format(
        user=user,
        group=group,
        working_directory=_systemd_path(working_directory),
        config_dir=_systemd_path(config_dir),
        data_dir=_systemd_path(data_dir),
        log_dir=_systemd_path(log_dir),
        exec_start=f"{_systemd_path(binary_path)} server",
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RoXX service helper")
    parser.add_argument(
        "command",
        choices=["print-systemd", "install", "remove", "status"],
        help="Service helper action",
    )
    parser.add_argument(
        "--binary",
        default="roxx",
        help="Path to the unified roxx application executable",
    )
    parser.add_argument("--user", default=os.getenv("USER", "roxx"), help="Service user")
    parser.add_argument("--group", default=os.getenv("USER", "roxx"), help="Service group")
    parser.add_argument("--working-directory", default=str(Path.cwd()), help="Working directory")
    parser.add_argument("--config-dir", default=os.getenv("ROXX_CONFIG_DIR", "/etc/roxx"))
    parser.add_argument("--data-dir", default=os.getenv("ROXX_DATA_DIR", "/var/lib/roxx"))
    parser.add_argument("--log-dir", default=os.getenv("ROXX_LOG_DIR", "/var/log/roxx"))
    parser.add_argument(
        "--unit-path",
        type=Path,
        default=Path("/etc/systemd/system/roxx.service"),
        help="systemd unit destination",
    )
    parser.add_argument("--dry-run", action="store_true", help="Render without changing systemd")
    return parser


def _render_from_args(args: argparse.Namespace) -> str:
    return render_systemd_unit(
        binary_path=Path(args.binary),
        user=args.user,
        group=args.group,
        working_directory=Path(args.working_directory),
        config_dir=Path(args.config_dir),
        data_dir=Path(args.data_dir),
        log_dir=Path(args.log_dir),
    )


def _require_systemd() -> None:
    if platform.system() != "Linux":
        raise SystemExit("systemd service commands are available only on Linux")


def install_systemd_unit(unit_path: Path, unit: str, dry_run: bool = False) -> None:
    _require_systemd()
    if dry_run:
        print(unit)
        return
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(unit, encoding="utf-8")
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", unit_path.stem], check=True)


def remove_systemd_unit(unit_path: Path, dry_run: bool = False) -> None:
    _require_systemd()
    if dry_run:
        print(f"Would disable and remove {unit_path}")
        return
    subprocess.run(["systemctl", "disable", "--now", unit_path.stem], check=False)
    unit_path.unlink(missing_ok=True)
    subprocess.run(["systemctl", "daemon-reload"], check=True)


def main() -> None:
    args = build_arg_parser().parse_args()
    if args.command == "print-systemd":
        print(_render_from_args(args))
    elif args.command == "install":
        install_systemd_unit(args.unit_path, _render_from_args(args), args.dry_run)
    elif args.command == "remove":
        remove_systemd_unit(args.unit_path, args.dry_run)
    elif args.command == "status":
        _require_systemd()
        raise SystemExit(subprocess.run(["systemctl", "status", args.unit_path.stem]).returncode)


if __name__ == "__main__":
    main()
