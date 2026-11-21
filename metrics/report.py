"""Deflection rate and time to provision, computed from the audit log."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp_server.audit.verify_chain import verify_chain
from mcp_server.catalog import JML_TOOLS


def build_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    deflected = _outcomes(records, "deflected")
    escalated = _outcomes(records, "escalated")
    automated = [
        record
        for record in records
        if record.get("phase") == "execute"
        and record.get("result") == "ok"
        and record.get("tool") in JML_TOOLS
        and (record.get("detail") or {}).get("outcome") == "automated"
    ]
    denominator = len(deflected) + len(escalated)
    rate = (len(deflected) / denominator) if denominator else None
    return {
        "deflected": len(deflected),
        "escalated": len(escalated),
        "automated_fulfillments": len(automated),
        "deflection_rate": rate,
        "median_time_to_provision_seconds": _median(_durations(records, "run_joiner")),
        "median_time_to_deprovision_seconds": _median(_durations(records, "run_leaver")),
        "median_approval_seconds": _median(_approval_wait(records)),
        "audit_entries": len(records),
    }


def report_for_path(path: Path) -> dict[str, Any]:
    status = verify_chain(path)
    records = _read(path)
    report = build_report(records)
    report["audit_chain_ok"] = status.ok
    report["audit_entries"] = status.entries
    return report


def render_text(report: dict[str, Any]) -> str:
    rate = report.get("deflection_rate")
    rate_text = "n/a" if rate is None else f"{rate:.0%}"
    lines = [
        "IT ops metrics (synthetic lab)",
        f"deflected: {report['deflected']}",
        f"escalated: {report['escalated']}",
        f"deflection_rate: {rate_text}",
        f"automated_fulfillments: {report['automated_fulfillments']}",
        f"median_time_to_provision_seconds: {_num(report['median_time_to_provision_seconds'])}",
        f"median_time_to_deprovision_seconds: {_num(report['median_time_to_deprovision_seconds'])}",
        f"median_approval_seconds: {_num(report['median_approval_seconds'])}",
        f"audit_entries: {report['audit_entries']}",
        f"audit_chain_ok: {report.get('audit_chain_ok', '')}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize a JML-Agent audit log.")
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    report = report_for_path(args.audit)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report.get("audit_chain_ok") else 1


def _outcomes(records: list[dict[str, Any]], outcome: str) -> list[dict[str, Any]]:
    return [record for record in records if (record.get("detail") or {}).get("outcome") == outcome]


def _durations(records: list[dict[str, Any]], tool: str) -> list[float]:
    started: dict[str, str] = {}
    durations: list[float] = []
    for record in records:
        if record.get("tool") != tool:
            continue
        approval_id = str(record.get("approval_id") or "")
        if record.get("phase") == "request" and approval_id:
            started[approval_id] = str(record["ts"])
        if record.get("phase") == "execute" and record.get("result") == "ok" and approval_id in started:
            durations.append(_seconds(started[approval_id], str(record["ts"])))
    return durations


def _approval_wait(records: list[dict[str, Any]]) -> list[float]:
    started: dict[str, str] = {}
    durations: list[float] = []
    for record in records:
        approval_id = str(record.get("approval_id") or "")
        if not approval_id:
            continue
        if record.get("phase") == "request":
            started[approval_id] = str(record["ts"])
        if record.get("phase") == "ready" and approval_id in started:
            durations.append(_seconds(started[approval_id], str(record["ts"])))
    return durations


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _seconds(start: str, end: str) -> float:
    return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _num(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}"


if __name__ == "__main__":
    sys.exit(main())
