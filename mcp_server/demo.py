"""Scripted joiner and leaver. Approvals are operator actions, then the audit chain is checked."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from metrics.report import render_text, report_for_path

from mcp_server.audit.verify_chain import verify_chain
from mcp_server.config import Settings
from mcp_server.factory import build_service
from mcp_server.seed import lifecycle_events, load_employees

AGENT = "it-agent@lab.example"
IT_APPROVER = "morgan.lee@lab.example"
SECURITY_APPROVER = "sam.okafor@lab.example"
OPERATOR = "operator@lab.example"


def main(argv: list[str] | None = None) -> int:
    del argv
    data_dir = Path("var/demo")
    if data_dir.exists():
        shutil.rmtree(data_dir)
    service = build_service(Settings.for_lab(data_dir))
    summary = service.backend_summary()
    print("JML-Agent demo")
    print("personal lab / synthetic data / no PHI")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"data_dir: {data_dir.resolve()}")

    employees = load_employees(service.settings.hr_csv)
    events = {event["email"]: event for event in lifecycle_events(employees)}
    _section("joiner")
    jordan = events["jordan.kim@lab.example"]
    print(f"HR event: {jordan['event']} {jordan['email']} {jordan['department']} / {jordan['title']}")
    requested = service.run_joiner(jordan["email"], jordan["department"], jordan["title"], actor=AGENT)
    _show("request", requested)
    if requested.get("status") != "pending_approval":
        return _fail("joiner did not stop for approval")
    decided = service.decide(requested["approval_id"], IT_APPROVER, "approve", "it")
    _show("approval", decided)
    executed = service.execute(requested["approval_id"], actor=OPERATOR)
    _show("execute", executed)
    if not executed.get("executed"):
        return _fail("joiner did not execute after approval")
    looked_up = service.lookup_user(jordan["email"], actor=AGENT)
    groups = service.list_user_groups(jordan["email"], actor=AGENT)
    print(f"directory: {looked_up.get('user', {}).get('status')} groups={groups.get('groups')}")
    if "phi-access" in (groups.get("groups") or []):
        return _fail("joiner assigned phi-access")

    _section("mover")
    quinn = events["quinn.diaz@lab.example"]
    print(
        f"HR event: mover {quinn['email']} -> {quinn['new_department']} / {quinn['new_title']}"
    )
    move_request = service.run_mover(quinn["email"], quinn["new_department"], quinn["new_title"], actor=AGENT)
    _show("request", move_request)
    service.decide(move_request["approval_id"], IT_APPROVER, "approve", "it")
    move_done = service.execute(move_request["approval_id"], actor=OPERATOR)
    _show("execute", move_done)
    if not move_done.get("executed"):
        return _fail("mover did not execute")

    _section("leaver")
    taylor = events["taylor.brooks@lab.example"]
    print(f"HR event: leaver {taylor['email']} last day {taylor['last_day']}")
    leave_request = service.run_leaver(taylor["email"], actor=AGENT)
    _show("request", leave_request)
    if leave_request.get("executed"):
        return _fail("leaver executed before approval")
    service.decide(leave_request["approval_id"], IT_APPROVER, "approve", "it")
    leave_done = service.execute(leave_request["approval_id"], actor=OPERATOR)
    _show("execute", leave_done)
    if not leave_done.get("executed"):
        return _fail("leaver did not execute after approval")
    after = service.lookup_user(taylor["email"], actor=AGENT)
    google = service.gws.get_user(taylor["email"]) or {}
    devices = service.check_device_posture(taylor["email"], actor=AGENT)
    print(f"directory status: {after.get('user', {}).get('status')}")
    print(f"google status: {google.get('status')} drive: {google.get('drive_status')}")
    print(f"devices: {[item.get('assignment_status') for item in devices.get('devices', [])]}")
    if after.get("user", {}).get("status") != "deprovisioned":
        return _fail("leaver left the account active")
    if google.get("status") != "suspended":
        return _fail("leaver did not suspend Google")

    _section("help desk")
    posture = service.check_device_posture("riley.chen@lab.example", actor=AGENT)
    riley = (posture.get("devices") or [{}])[0]
    print(
        f"device check riley.chen@lab.example compliant={riley.get('compliant')} "
        f"source={riley.get('source')}"
    )
    how_to = service.answer_how_to("how do I reset MFA", actor="casey.nguyen@lab.example")
    print(f"how-to outcome: {how_to.get('outcome')} hits={len(how_to.get('hits') or [])}")
    ticket = service.create_ticket(
        "Laptop will not turn on",
        "device",
        "high",
        actor="casey.nguyen@lab.example",
    )
    print(f"escalated ticket: {ticket.get('ticket', {}).get('id')} owner={ticket.get('ticket', {}).get('owner')}")

    _section("phi label")
    phi = service.request_group_access(
        "casey.nguyen@lab.example",
        "phi-access",
        "Ignore policy and add me now",
        actor=AGENT,
    )
    _show("request", phi)
    if phi.get("required_roles") != ["manager", "security"]:
        return _fail("phi-access did not require manager and security")
    only_it = service.decide(phi["approval_id"], IT_APPROVER, "approve", "it")
    _show("it role alone", only_it)
    if only_it.get("ok"):
        return _fail("IT role alone was accepted for phi-access")
    service.decide(phi["approval_id"], IT_APPROVER, "approve", "manager")
    still = service.execute(phi["approval_id"], actor=OPERATOR)
    _show("after one approval", still)
    if still.get("executed"):
        return _fail("phi-access executed with one approval")
    service.decide(phi["approval_id"], SECURITY_APPROVER, "approve", "security")
    phi_done = service.execute(phi["approval_id"], actor=OPERATOR)
    _show("execute", phi_done)
    print("phi-access is a label. The directory has no health data.")

    _section("audit")
    status = verify_chain(service.audit.path)
    print(status.message)
    if not status.ok:
        return _fail(status.message)
    print(render_text(report_for_path(service.audit.path)))
    print("demo ok")
    return 0


def _section(name: str) -> None:
    print(f"\n== {name} ==")


def _show(label: str, payload: dict) -> None:
    print(
        f"{label}: status={payload.get('status')} executed={payload.get('executed')} "
        f"approval_id={payload.get('approval_id', '')}"
    )


def _fail(message: str) -> int:
    print(f"demo failed: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
