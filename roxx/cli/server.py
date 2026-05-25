"""Dedicated RoXX web server entry point."""

from __future__ import annotations

import sys

from roxx.server.runtime import run_web_server


def main() -> None:
    try:
        raise_code = run_web_server()
    except KeyboardInterrupt:
        raise_code = 0
    except Exception as exc:  # pragma: no cover - terminal failure path
        print(f"[RoXX] Server startup failed: {exc}", file=sys.stderr)
        raise_code = 1
    raise SystemExit(raise_code)


if __name__ == "__main__":
    main()

