"""Audit export commands for SIEM and archival pipelines."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from roxx.core.audit.db import AuditDatabase


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RoXX audit pipeline helper")
    parser.add_argument("command", choices=["export"], help="Audit action")
    parser.add_argument("--output", type=Path, help="JSONL destination; defaults to stdout")
    parser.add_argument("--limit", type=int, default=10_000)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    records = AuditDatabase.get_logs(limit=max(1, args.limit))
    lines = "".join(json.dumps(record, sort_keys=True) + "\n" for record in reversed(records))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(lines, encoding="utf-8")
    else:
        sys.stdout.write(lines)


if __name__ == "__main__":
    main()
