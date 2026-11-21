from __future__ import annotations

from pathlib import Path

from mcp_server.audit.log import AuditLog
from mcp_server.audit.verify_chain import verify_chain


def test_chain_validates_and_detects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    log.append(actor="a@lab.example", tool="lookup_user", phase="complete", effect="allow", result="ok")
    log.append(actor="a@lab.example", tool="lookup_user", phase="complete", effect="allow", result="ok")
    status = verify_chain(path)
    assert status.ok
    assert status.entries == 2

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    lines[0] = lines[0].replace("lookup_user", "lookup_xxxx", 1)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    broken = verify_chain(path)
    assert not broken.ok
    assert "hash mismatch" in broken.message


def test_deleted_line_breaks_the_chain(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    for _ in range(3):
        log.append(actor="a@lab.example", tool="lookup_user", phase="complete", effect="allow", result="ok")
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text(lines[0] + "\n" + lines[2] + "\n", encoding="utf-8")
    status = verify_chain(path)
    assert not status.ok
