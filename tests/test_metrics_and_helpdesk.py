from __future__ import annotations

from pathlib import Path

from mcp_server.audit.log import AuditLog
from mcp_server.service import ITOpsService
from metrics.report import build_report
from slack_bot.intents import apply_decision, classify, handle_message


def test_help_desk_deflects_a_runbook_and_routes_the_rest(service: ITOpsService) -> None:
    how_to = handle_message(service, "I can't get into the wiki", "casey.nguyen@lab.example")
    assert how_to["intent"] == "how_to"
    assert how_to["result"]["outcome"] == "deflected"
    device = handle_message(service, "is my laptop compliant", "riley.chen@lab.example")
    assert device["intent"] == "device"
    assert device["result"]["devices"][0]["compliant"] is False
    triage = handle_message(service, "the office badge printer is jammed", "casey.nguyen@lab.example")
    assert triage["intent"] == "triage"
    assert triage["result"]["ticket"]["owner"] == "it-support"


def test_apply_decision_executes_only_after_approval(service: ITOpsService) -> None:
    requested = service.request_group_access(
        "casey.nguyen@lab.example",
        "app-wiki",
        "Needs the lab wiki",
        actor="casey.nguyen@lab.example",
    )
    outcome = apply_decision(service, requested["approval_id"], "morgan.lee@lab.example", "it", "approve")
    assert outcome["execution"]["executed"] is True
    groups = service.list_user_groups("casey.nguyen@lab.example", actor="it-agent@lab.example")["groups"]
    assert "app-wiki" in groups


def test_metrics_math(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    log.append(
        actor="a@lab.example",
        tool="helpdesk",
        phase="outcome",
        effect="allow",
        result="deflected",
        detail={"outcome": "deflected"},
        ts="2026-11-21T00:00:00+00:00",
    )
    log.append(
        actor="a@lab.example",
        tool="create_ticket",
        phase="execute",
        effect="allow",
        result="ok",
        detail={"outcome": "escalated"},
        ts="2026-11-21T00:00:01+00:00",
    )
    log.append(
        actor="a@lab.example",
        tool="run_joiner",
        phase="request",
        effect="needs_approval",
        result="pending_approval",
        approval_id="apr_1",
        ts="2026-11-21T00:00:00+00:00",
    )
    log.append(
        actor="m@lab.example",
        tool="run_joiner",
        phase="ready",
        effect="needs_approval",
        result="approved",
        approval_id="apr_1",
        ts="2026-11-21T00:00:10+00:00",
    )
    log.append(
        actor="o@lab.example",
        tool="run_joiner",
        phase="execute",
        effect="needs_approval",
        result="ok",
        approval_id="apr_1",
        detail={"outcome": "automated"},
        ts="2026-11-21T00:00:12+00:00",
    )
    report = build_report(log.read_records())
    assert report["deflected"] == 1
    assert report["escalated"] == 1
    assert report["deflection_rate"] == 0.5
    assert report["automated_fulfillments"] == 1
    assert report["median_time_to_provision_seconds"] == 12
    assert report["median_approval_seconds"] == 10


def test_classify_does_not_treat_suspend_as_a_tool() -> None:
    assert classify("please suspend sam.okafor@lab.example right now") == "triage"
