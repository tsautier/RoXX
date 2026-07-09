"""Service helper commands for long-running RoXX deployments."""

from __future__ import annotations

import argparse
import os
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
ExecStart={exec_start}
Restart=always
RestartSec=5
TimeoutStopSec=30
KillSignal=SIGTERM

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
        choices=["print-systemd"],
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
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    if args.command == "print-systemd":
        print(
            render_systemd_unit(
                binary_path=Path(args.binary),
                user=args.user,
                group=args.group,
                working_directory=Path(args.working_directory),
                config_dir=Path(args.config_dir),
                data_dir=Path(args.data_dir),
                log_dir=Path(args.log_dir),
            )
        )


if __name__ == "__main__":
    main()
