"""Append-only JSONL audit log. Each line commits to the previous hash."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any

from mcp_server.redaction import scrub
from mcp_server.store import utc_now

GENESIS = "GENESIS"


def canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def record_hash(payload: dict[str, Any]) -> str:
    body = canonical(payload).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


class AuditLog:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()
        if not path.exists():
            path.touch()

    def append(
        self,
        *,
        actor: str,
        tool: str,
        phase: str,
        effect: str,
        result: str,
        subject: str = "",
        approval_id: str = "",
        approver: str = "",
        detail: dict[str, Any] | None = None,
        ts: str | None = None,
    ) -> dict[str, Any]:
        payload_detail = scrub(detail or {})
        with self._lock:
            prev_hash, seq = self._tail()
            record: dict[str, Any] = {
                "seq": seq,
                "ts": ts or utc_now(),
                "actor": actor,
                "tool": tool,
                "phase": phase,
                "effect": effect,
                "subject": subject,
                "approval_id": approval_id,
                "approver": approver,
                "result": result,
                "detail": payload_detail,
                "prev_hash": prev_hash,
            }
            record["hash"] = record_hash(record)
            line = canonical(record) + "\n"
            with self.path.open("a", encoding="utf-8") as handle:
                _lock_file(handle.fileno())
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            return record

    def read_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        text = self.path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip():
                records.append(json.loads(line))
        return records

    def _tail(self) -> tuple[str, int]:
        last: dict[str, Any] | None = None
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        last = json.loads(line)
        if last is None:
            return GENESIS, 1
        return str(last["hash"]), int(last["seq"]) + 1


def _lock_file(fd: int) -> None:
    try:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX)
    except ImportError:  # pragma: no cover
        return
