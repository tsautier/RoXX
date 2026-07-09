"""RoXX main entry point."""

import argparse
import sys
from collections.abc import Callable


def _run_with_forwarded_argv(command_name: str, command_main: Callable[[], None], args: list[str]) -> None:
    """Run a delegated CLI command while preserving its native argument parsing."""
    original_argv = sys.argv[:]
    sys.argv = [command_name, *args]
    try:
        command_main()
    finally:
        sys.argv = original_argv


def main():
    """Main entry point for the `roxx` command."""
    parser = argparse.ArgumentParser(prog="roxx", add_help=True)
    parser.add_argument(
        "mode",
        nargs="?",
        default="console",
        choices=["console", "server", "service", "setup", "windows-service"],
        help=(
            "Launch the interactive console, web server, Linux service helpers, "
            "setup assistant, or Windows service helper"
        ),
    )
    args, forwarded_args = parser.parse_known_args()

    try:
        if args.mode == "server":
            from roxx.cli.server import main as server_main

            _run_with_forwarded_argv("roxx server", server_main, forwarded_args)
        elif args.mode == "service":
            from roxx.cli.service import main as service_main

            _run_with_forwarded_argv("roxx service", service_main, forwarded_args)
        elif args.mode == "setup":
            from roxx.cli.setup import main as setup_main

            _run_with_forwarded_argv("roxx setup", setup_main, forwarded_args)
        elif args.mode == "windows-service":
            from roxx.cli.windows_service import main as windows_service_main

            _run_with_forwarded_argv(
                "roxx windows-service",
                windows_service_main,
                forwarded_args,
            )
        else:
            from roxx.cli.console import main as console_main

            _run_with_forwarded_argv("roxx", console_main, forwarded_args)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
