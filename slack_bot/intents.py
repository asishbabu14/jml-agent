"""Deterministic help-desk intents. Free text never becomes an approval."""

from __future__ import annotations

import re
from typing import Any

from mcp_server.catalog import GROUP_NAMES, KNOWN_DEPARTMENTS
from mcp_server.service import ITOpsService

_EMAIL = re.compile(r"[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_TITLE = re.compile(r"(?i)\btitle\s+([A-Za-z][A-Za-z ]{1,60})")


def classify(text: str) -> str:
    lowered = text.lower()
    if any(phrase in lowered for phrase in ("how do i", "how do we", "can't get into", "cannot get into")):
        return "how_to"
    if "mfa" in lowered or "multi-factor" in lowered or "reset my factor" in lowered:
        return "mfa"
    if any(word in lowered for word in ("laptop", "device", "filevault")):
        return "device"
    if any(word in lowered for word in ("offboard", "last day", "leaver", "leaving")):
        return "leaver"
    if any(phrase in lowered for phrase in ("new hire", "onboard", "joiner", "starting monday")):
        return "joiner"
    if any(phrase in lowered for phrase in ("mover", "changed department", "moved to")):
        return "mover"
    if any(phrase in lowered for phrase in ("access", "add me", "add to", "group")):
        return "access"
    return "triage"


def handle_message(service: ITOpsService, text: str, requester: str) -> dict[str, Any]:
    """Answer or open a request. This function never approves or executes."""
    intent = classify(text)
    if intent == "how_to":
        result = service.answer_how_to(text, actor=requester)
        return {"intent": intent, "result": result, "reply": _reply_how_to(result)}
    if intent == "device":
        email = _email(text) or requester
        result = service.check_device_posture(email, actor=requester)
        return {"intent": intent, "result": result, "reply": _reply_device(result)}
    if intent == "mfa":
        email = _email(text) or requester
        result = service.reset_mfa(email, actor=requester)
        return {"intent": intent, "result": result, "reply": _reply_pending(result, "MFA reset")}
    if intent == "access":
        group = _group(text)
        email = _email(text) or requester
        if group is None:
            return {
                "intent": intent,
                "result": None,
                "reply": "Tell me which catalog group, for example app-wiki.",
            }
        result = service.request_group_access(email, group, reason=text[:500], actor=requester)
        return {"intent": intent, "result": result, "reply": _reply_pending(result, f"access to {group}")}
    if intent == "joiner":
        email = _email(text)
        if email is None:
            return {"intent": intent, "result": None, "reply": "I need the new hire's email address."}
        hr = service.store.get_hr(email) or {}
        department = _department(text) or hr.get("department") or ""
        title = _title(text) or hr.get("title") or ""
        if not department or not title:
            return {"intent": intent, "result": None, "reply": "I need a department and a title from the HR feed."}
        result = service.run_joiner(email, department, title, actor=requester)
        return {"intent": intent, "result": result, "reply": _reply_pending(result, "joiner")}
    if intent == "leaver":
        email = _email(text)
        if email is None:
            return {"intent": intent, "result": None, "reply": "I need the email address for the leaver."}
        result = service.run_leaver(email, actor=requester)
        return {"intent": intent, "result": result, "reply": _reply_pending(result, "leaver")}
    if intent == "mover":
        email = _email(text)
        if email is None:
            return {"intent": intent, "result": None, "reply": "I need the email address for the move."}
        hr = service.store.get_hr(email) or {}
        department = _department(text) or hr.get("new_department") or ""
        title = _title(text) or hr.get("new_title") or ""
        if not department or not title:
            return {"intent": intent, "result": None, "reply": "I need the new department and title."}
        result = service.run_mover(email, department, title, actor=requester)
        return {"intent": intent, "result": result, "reply": _reply_pending(result, "mover")}
    result = service.create_ticket(text[:300], "other", "normal", actor=requester)
    ticket = result.get("ticket") or {}
    return {
        "intent": intent,
        "result": result,
        "reply": f"I opened {ticket.get('id', 'a ticket')} and routed it to {ticket.get('owner', 'IT')}.",
    }


def apply_decision(
    service: ITOpsService,
    approval_id: str,
    approver: str,
    role: str,
    decision: str,
    *,
    identity_verified: bool = False,
    verification_method: str = "",
) -> dict[str, Any]:
    """Called from a Slack button click, with the clicker's email, not model text."""
    recorded = service.decide(
        approval_id,
        approver,
        decision,
        role,
        identity_verified=identity_verified,
        verification_method=verification_method,
    )
    if recorded.get("status") == "approved":
        executed = service.execute(approval_id, actor=approver)
        return {"decision": recorded, "execution": executed}
    return {"decision": recorded, "execution": None}


def _email(text: str) -> str | None:
    match = _EMAIL.search(text)
    return match.group(0).lower() if match else None


def _group(text: str) -> str | None:
    lowered = text.lower()
    found = [name for name in GROUP_NAMES if name in lowered]
    if not found:
        return None
    return sorted(found, key=len, reverse=True)[0]


def _department(text: str) -> str | None:
    for name in sorted(KNOWN_DEPARTMENTS, key=len, reverse=True):
        if name.lower() in text.lower():
            return name
    return None


def _title(text: str) -> str | None:
    match = _TITLE.search(text)
    return match.group(1).strip() if match else None


def _reply_pending(result: dict[str, Any], label: str) -> str:
    if result.get("status") == "pending_approval":
        roles = ", ".join(result.get("required_roles") or [])
        return (
            f"I requested {label}. It is not done. "
            f"Approval id {result.get('approval_id')} needs: {roles}."
        )
    return f"I could not request {label}. {result.get('message', '')}"


def _reply_how_to(result: dict[str, Any]) -> str:
    if result.get("outcome") == "deflected" and result.get("hits"):
        hit = result["hits"][0]
        return f"From the runbook '{hit['title']}': {hit['excerpt'][:400]}"
    ticket = (result.get("ticket") or {}).get("ticket") or result.get("ticket") or {}
    return f"I could not find a runbook. Ticket {ticket.get('id', '')} is with {ticket.get('owner', 'IT')}."


def _reply_device(result: dict[str, Any]) -> str:
    devices = result.get("devices") or []
    if not devices:
        return "No device is assigned in the mock inventory."
    device = devices[0]
    return (
        f"Mock inventory ({device.get('source')}): {device.get('platform')} "
        f"{device.get('os_version')}, compliant={device.get('compliant')}, "
        f"assignment={device.get('assignment_status')}."
    )
