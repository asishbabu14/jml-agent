"""Operator CLI for approvals. This is not an MCP tool."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mcp_server.config import Settings
from mcp_server.factory import build_service


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record or execute a JML-Agent approval.")
    parser.add_argument("--data-dir", required=True, type=Path)
    sub = parser.add_subparsers(dest="cmd", required=True)

    decide = sub.add_parser("decide")
    decide.add_argument("--id", required=True)
    decide.add_argument("--approver", required=True)
    decide.add_argument("--decision", required=True, choices=["approve", "deny"])
    decide.add_argument("--role", required=True)
    decide.add_argument("--identity-verified", action="store_true")
    decide.add_argument("--verification-method", default="")
    decide.add_argument("--note", default="")

    execute = sub.add_parser("execute")
    execute.add_argument("--id", required=True)
    execute.add_argument("--actor", required=True)

    args = parser.parse_args(argv)
    service = build_service(Settings.for_lab(args.data_dir))
    if args.cmd == "decide":
        result = service.decide(
            args.id,
            args.approver,
            args.decision,
            args.role,
            identity_verified=args.identity_verified,
            verification_method=args.verification_method,
            note=args.note,
        )
    else:
        result = service.execute(args.id, actor=args.actor)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
