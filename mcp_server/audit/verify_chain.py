"""Recompute the hash chain. A changed or missing line fails the check."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from mcp_server.audit.log import GENESIS, canonical, record_hash


@dataclass(frozen=True)
class ChainStatus:
    ok: bool
    entries: int
    message: str


def verify_chain(path: Path) -> ChainStatus:
    if not path.exists() or path.stat().st_size == 0:
        return ChainStatus(True, 0, "audit chain valid (0 entries)")
    expected_prev = GENESIS
    expected_seq = 1
    count = 0
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            return ChainStatus(False, count, f"line {line_number}: not JSON")
        stored = record.get("hash")
        payload = {key: value for key, value in record.items() if key != "hash"}
        actual = record_hash(payload)
        if stored != actual or canonical(record) != raw:
            return ChainStatus(False, count, f"line {line_number}: hash mismatch")
        if payload.get("prev_hash") != expected_prev:
            return ChainStatus(False, count, f"line {line_number}: prev_hash does not match")
        if payload.get("seq") != expected_seq:
            return ChainStatus(False, count, f"line {line_number}: sequence gap")
        expected_prev = str(stored)
        expected_seq += 1
        count += 1
    return ChainStatus(True, count, f"audit chain valid ({count} entries)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the JML-Agent audit hash chain.")
    parser.add_argument("--audit", required=True, type=Path)
    args = parser.parse_args(argv)
    status = verify_chain(args.audit)
    print(status.message)
    return 0 if status.ok else 1


if __name__ == "__main__":
    sys.exit(main())
