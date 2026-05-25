"""RoXX main entry point."""

import sys
import argparse


def main():
    """Main entry point for the `roxx` command."""
    parser = argparse.ArgumentParser(prog="roxx", add_help=True)
    parser.add_argument(
        "mode",
        nargs="?",
        default="console",
        choices=["console", "server", "service"],
        help="Launch the interactive console, the web server, or service helpers",
    )
    args = parser.parse_args()

    try:
        if args.mode == "server":
            from roxx.cli.server import main as server_main

            server_main()
        elif args.mode == "service":
            from roxx.cli.service import main as service_main

            service_main()
        else:
            from roxx.cli.console import main as console_main

            console_main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
