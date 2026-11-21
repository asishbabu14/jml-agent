"""Print joiner, mover, and leaver events from the synthetic CSV."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mcp_server.seed import lifecycle_events, load_employees

DEFAULT_CSV = Path(__file__).with_name("employees.csv")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit synthetic HR lifecycle events.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args(argv)
    for event in lifecycle_events(load_employees(args.csv)):
        print(json.dumps(event, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
