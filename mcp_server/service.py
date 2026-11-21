"""IT operations service. Policy, approval, and audit run here, not in the model."""

from __future__ import annotations

from typing import Any

from mcp_server.adapters.gws_mock import GoogleWorkspaceMock
from mcp_server.adapters.mdm_mock import DeviceMock
from mcp_server.adapters.okta_live import OktaLiveError
from mcp_server.adapters.tickets import TicketStore
from mcp_server.audit.log import AuditLog
from mcp_server.catalog import (
    IDENTITY_VERIFICATION_METHODS,
    groups_for,
)
from mcp_server.config import Settings
from mcp_server.policy.engine import Decision, PolicyEngine
from mcp_server.redaction import device_view, redact_text, user_view
from mcp_server.runbook_search import search as search_files
from mcp_server.store import Store, new_id, utc_now
from mcp_server.validate import InputError
from mcp_server.validate import category as parse_category
from mcp_server.validate import department as parse_department
from mcp_server.validate import email as parse_email
from mcp_server.validate import group_name as parse_group
from mcp_server.validate import query as parse_query
from mcp_server.validate import reason as parse_reason
from mcp_server.validate import summary as parse_summary
from mcp_server.validate import title as parse_title
from mcp_server.validate import urgency as parse_urgency


class ITOpsService:
    def __init__(
        self,
        settings: Settings,
        store: Store,
        policy: PolicyEngine,
        audit: AuditLog,
        okta: Any,
        gws: GoogleWorkspaceMock,
        devices: DeviceMock,
        tickets: TicketStore,
    ) -> None:
        self.settings = settings
        self.store = store
        self.policy = policy
        self.audit = audit
        self.okta = okta
        self.gws = gws
        self.devices = devices
        self.tickets = tickets

    def backend_summary(self) -> dict[str, str]:
        return {
            "identity": f"{self.okta.backend_label} ({self.okta.backend_name})",
            "google_workspace": f"{self.gws.backend_label} ({self.gws.backend_name})",
            "mdm": f"{self.devices.backend_label} ({self.devices.backend_name})",
            "tickets": f"{self.tickets.backend_label} ({self.tickets.backend_name})",
            "live_okta": "yes" if self.settings.live_okta else "no",
        }

    def lookup_user(self, email: str, actor: str) -> dict[str, Any]:
        try:
            email = parse_email(email)
        except InputError as exc:
            return self._invalid("lookup_user", actor, exc.message)
        gated = self._authorize("lookup_user", actor, email, {"email": email})
        if gated:
            return gated
        user = self._safe_user(email)
        view = user_view(user)
        self._audit(actor, "lookup_user", "complete", "allow", "ok" if view else "not_found", email)
        if view is None:
            return {
                "ok": True,
                "status": "not_found",
                "executed": False,
                "effect": "allow",
                "user": None,
                "message": "No directory user for that email.",
            }
        return {"ok": True, "status": "ok", "executed": False, "effect": "allow", "user": view}

    def list_user_groups(self, email: str, actor: str) -> dict[str, Any]:
        try:
            email = parse_email(email)
        except InputError as exc:
            return self._invalid("list_user_groups", actor, exc.message)
        gated = self._authorize("list_user_groups", actor, email, {"email": email})
        if gated:
            return gated
        user = self._safe_user(email)
        try:
            groups = [] if user is None else self.okta.list_groups(email)
        except OktaLiveError as exc:
            return {"ok": False, "status": "error", "executed": False, "message": str(exc)[:200]}
        self._audit(actor, "list_user_groups", "complete", "allow", "ok", email, {"groups": groups})
        return {
            "ok": True,
            "status": "ok" if user else "not_found",
            "executed": False,
            "effect": "allow",
            "email": email,
            "groups": groups,
        }

    def check_device_posture(self, email: str, actor: str) -> dict[str, Any]:
        try:
            email = parse_email(email)
        except InputError as exc:
            return self._invalid("check_device_posture", actor, exc.message)
        gated = self._authorize("check_device_posture", actor, email, {"email": email})
        if gated:
            return gated
        devices = [device_view(row) for row in self.devices.for_user(email)]
        self._audit(
            actor,
            "check_device_posture",
            "complete",
            "allow",
            "ok" if devices else "no_device",
            email,
        )
        return {
            "ok": True,
            "status": "ok" if devices else "no_device",
            "executed": False,
            "effect": "allow",
            "source": self.devices.source,
            "devices": devices,
        }

    def search_runbooks(self, query: str, actor: str) -> dict[str, Any]:
        try:
            query = parse_query(query)
        except InputError as exc:
            return self._invalid("search_runbooks", actor, exc.message)
        gated = self._authorize("search_runbooks", actor, "", {"query": query})
        if gated:
            return gated
        hits = search_files(self.settings.runbook_dir, query)
        self._audit(actor, "search_runbooks", "complete", "allow", "ok", "", {"hits": len(hits)})
        return {"ok": True, "status": "ok", "executed": False, "effect": "allow", "hits": hits}

    def answer_how_to(self, query: str, actor: str) -> dict[str, Any]:
        found = self.search_runbooks(query, actor=actor)
        if not found.get("ok"):
            return found
        if found["hits"]:
            self._audit(
                actor,
                "helpdesk",
                "outcome",
                "allow",
                "deflected",
                "",
                {"outcome": "deflected", "query": query[:120]},
            )
            return {**found, "outcome": "deflected", "message": "Answered from a runbook."}
        ticket = self.create_ticket(query, "how_to", "normal", actor=actor)
        return {"ok": True, "outcome": "escalated", "hits": [], "ticket": ticket}

    def create_ticket(self, summary: str, category: str, urgency: str, actor: str) -> dict[str, Any]:
        try:
            summary = redact_text(parse_summary(summary))
            category = parse_category(category)
            urgency = parse_urgency(urgency)
            actor = parse_email(actor)
        except InputError as exc:
            return self._invalid("create_ticket", actor, exc.message)
        gated = self._authorize("create_ticket", actor, actor, {"category": category})
        if gated:
            return gated
        ticket = self.tickets.create(summary, category, urgency, actor)
        self._audit(
            actor,
            "create_ticket",
            "execute",
            "allow",
            "ok",
            actor,
            {"outcome": "escalated", "ticket_id": ticket["id"], "owner": ticket["owner"], "category": category},
        )
        return {
            "ok": True,
            "status": "open",
            "executed": True,
            "effect": "allow",
            "ticket": ticket,
            "message": "Ticket opened and routed. No identity change was made.",
        }

    def request_group_access(self, email: str, group: str, reason: str, actor: str) -> dict[str, Any]:
        try:
            email = parse_email(email)
            group = parse_group(group)
            reason = redact_text(parse_reason(reason))
        except InputError as exc:
            return self._invalid("request_group_access", actor, exc.message)
        if self._safe_user(email) is None:
            return self._invalid("request_group_access", actor, "That person is not in the directory.", email)
        params = {"email": email, "group": group, "reason": reason}
        return self._start_or_run("request_group_access", actor, email, params)

    def reset_mfa(self, email: str, actor: str) -> dict[str, Any]:
        try:
            email = parse_email(email)
        except InputError as exc:
            return self._invalid("reset_mfa", actor, exc.message)
        user = self._safe_user(email)
        if user is None or user.get("status") not in {"active", None}:
            return self._invalid("reset_mfa", actor, "MFA reset needs an active directory user.", email)
        return self._start_or_run("reset_mfa", actor, email, {"email": email})

    def run_joiner(self, email: str, department: str, title: str, actor: str) -> dict[str, Any]:
        try:
            email = parse_email(email)
            department = parse_department(department)
            title = parse_title(title)
        except InputError as exc:
            return self._invalid("run_joiner", actor, exc.message)
        hr = self.store.get_hr(email)
        if hr is None:
            return self._invalid("run_joiner", actor, "That email is not in the HR feed.", email)
        if hr["status"] in {"leaving", "mover"}:
            return self._invalid("run_joiner", actor, "HR status does not allow a joiner for this person.", email)
        params = {"email": email, "department": department, "title": title}
        return self._start_or_run("run_joiner", actor, email, params)

    def run_mover(self, email: str, department: str, title: str, actor: str) -> dict[str, Any]:
        try:
            email = parse_email(email)
            department = parse_department(department)
            title = parse_title(title)
        except InputError as exc:
            return self._invalid("run_mover", actor, exc.message)
        if self.store.get_hr(email) is None:
            return self._invalid("run_mover", actor, "That email is not in the HR feed.", email)
        user = self._safe_user(email)
        if user is None or user.get("status") != "active":
            return self._invalid("run_mover", actor, "Mover needs an active directory user.", email)
        params = {"email": email, "department": department, "title": title}
        return self._start_or_run("run_mover", actor, email, params)

    def run_leaver(self, email: str, actor: str) -> dict[str, Any]:
        try:
            email = parse_email(email)
        except InputError as exc:
            return self._invalid("run_leaver", actor, exc.message)
        if self.store.get_hr(email) is None:
            return self._invalid("run_leaver", actor, "That email is not in the HR feed.", email)
        if self._safe_user(email) is None:
            return self._invalid("run_leaver", actor, "That person is not in the directory.", email)
        return self._start_or_run("run_leaver", actor, email, {"email": email})

    def suspend_user(self, email: str, actor: str) -> dict[str, Any]:
        try:
            email = parse_email(email)
        except InputError as exc:
            return self._invalid("suspend_user", actor, exc.message)
        user = self._safe_user(email)
        if user is None or user.get("status") != "active":
            return self._invalid("suspend_user", actor, "Suspend needs an active directory user.", email)
        return self._start_or_run("suspend_user", actor, email, {"email": email})

    def decide(
        self,
        approval_id: str,
        approver: str,
        decision: str,
        role: str,
        *,
        identity_verified: bool = False,
        verification_method: str = "",
        note: str = "",
    ) -> dict[str, Any]:
        """Record a human decision. The model is not given this method as a tool."""
        approval = self.store.get_approval(approval_id)
        if approval is None:
            return {"ok": False, "status": "not_found", "executed": False, "message": "Unknown approval."}
        if approval["status"] != "pending":
            return {
                "ok": False,
                "status": approval["status"],
                "executed": False,
                "message": "This approval is no longer pending.",
            }
        try:
            approver = parse_email(approver)
        except InputError as exc:
            return self._invalid("decide_approval", approver, exc.message, approval["subject_email"])
        choice = decision.strip().lower()
        if choice not in {"approve", "deny"}:
            return self._invalid("decide_approval", approver, "Decision must be approve or deny.")
        policy = self.policy.evaluate(approval["tool"], approval["params"])
        if policy.effect == "deny":
            self.store.set_approval_status(approval_id, "denied")
            self._audit(
                approver,
                approval["tool"],
                "deny",
                "deny",
                "denied",
                approval["subject_email"],
                approval_id=approval_id,
            )
            return {"ok": False, "status": "denied", "executed": False, "effect": "deny", "message": policy.reason}
        if role not in policy.required_roles:
            return self._reject_decision(approval, approver, "That role is not an approver for this request.")
        if approver not in self.policy.role_members(role):
            return self._reject_decision(approval, approver, "That person is not on the approver roster for this role.")
        if approver == approval["requester"]:
            return self._reject_decision(approval, approver, "The requester cannot approve their own request.")
        existing = self.store.decisions_for(approval_id)
        if any(row["approver"] == approver for row in existing):
            return self._reject_decision(approval, approver, "This person has already decided.")
        if policy.distinct_roles and any(row["role"] == role and row["decision"] == "approve" for row in existing):
            return self._reject_decision(approval, approver, "That role has already approved.")
        method = verification_method.strip().lower()
        if choice == "approve" and policy.identity_verification:
            if not identity_verified or method not in IDENTITY_VERIFICATION_METHODS:
                return self._reject_decision(
                    approval,
                    approver,
                    "MFA reset needs identity_verified and a method of video, in_person, or manager_callback.",
                )
        note = redact_text(note.strip())[:300]
        self.store.add_decision(
            {
                "approval_id": approval_id,
                "approver": approver,
                "role": role,
                "decision": choice,
                "identity_verified": bool(identity_verified),
                "verification_method": method,
                "note": note,
                "created_at": utc_now(),
            }
        )
        decisions = self.store.decisions_for(approval_id)
        if choice == "deny":
            self.store.set_approval_status(approval_id, "denied")
            status = "denied"
        elif self._satisfied(decisions, policy):
            self.store.set_approval_status(approval_id, "approved")
            status = "approved"
        else:
            status = "pending"
        self._audit(
            approver,
            approval["tool"],
            "decide",
            policy.effect,
            status,
            approval["subject_email"] or "",
            {"role": role},
            approval_id=approval_id,
            approver=approver,
        )
        if status == "approved":
            self._audit(
                approver,
                approval["tool"],
                "ready",
                policy.effect,
                "approved",
                approval["subject_email"] or "",
                approval_id=approval_id,
                approver=approver,
            )
        return {
            "ok": True,
            "status": status,
            "executed": False,
            "effect": policy.effect,
            "approval_id": approval_id,
            "message": "Decision recorded. Nothing has been changed in the directory yet.",
        }

    def execute(self, approval_id: str, actor: str) -> dict[str, Any]:
        """Run an already-approved action. Arguments come from the stored request."""
        approval = self.store.get_approval(approval_id)
        if approval is None:
            return {"ok": False, "status": "not_found", "executed": False, "message": "Unknown approval."}
        if approval["status"] == "executed":
            return {
                "ok": True,
                "status": "executed",
                "executed": True,
                "idempotent": True,
                "approval_id": approval_id,
                "result": approval["result"],
            }
        if approval["status"] in {"denied", "failed"}:
            return {
                "ok": False,
                "status": approval["status"],
                "executed": False,
                "message": "This request cannot be executed.",
            }
        policy = self.policy.evaluate(approval["tool"], approval["params"])
        subject = approval["subject_email"] or ""
        if policy.effect == "deny":
            self.store.set_approval_status(approval_id, "denied")
            self._audit(actor, approval["tool"], "deny", "deny", "denied", subject, approval_id=approval_id)
            return {"ok": False, "status": "denied", "executed": False, "effect": "deny", "message": policy.reason}
        missing = self._missing_scopes(approval["tool"])
        if missing:
            self._audit(
                actor,
                approval["tool"],
                "deny",
                "deny",
                "scope_not_granted",
                subject,
                {"missing_scopes": missing},
                approval_id=approval_id,
            )
            return {
                "ok": False,
                "status": "scope_not_granted",
                "executed": False,
                "missing_scopes": missing,
                "message": "Configured scopes do not cover this action.",
            }
        if policy.effect == "needs_approval":
            if approval["status"] != "approved" or not self._satisfied(self.store.decisions_for(approval_id), policy):
                return {
                    "ok": False,
                    "status": "pending_approval",
                    "executed": False,
                    "effect": "needs_approval",
                    "message": "Approval is not complete. The change has not been made.",
                }
        result = self._dispatch(approval["tool"], approval["params"])
        status = "executed" if result.get("ok") else "failed"
        self.store.set_approval_status(approval_id, status, result)
        detail = {**_public_result(result), "outcome": "automated" if result.get("ok") else "error"}
        self._audit(
            actor,
            approval["tool"],
            "execute",
            policy.effect,
            "ok" if result.get("ok") else "error",
            subject,
            detail,
            approval_id=approval_id,
        )
        return {
            "ok": bool(result.get("ok")),
            "status": status,
            "executed": bool(result.get("ok")),
            "effect": policy.effect,
            "approval_id": approval_id,
            "result": result,
        }

    def _start_or_run(self, tool: str, actor: str, subject: str, params: dict[str, Any]) -> dict[str, Any]:
        gated = self._authorize(tool, actor, subject, params)
        if gated:
            return gated
        result = self._dispatch(tool, params)
        detail = {**_public_result(result), "outcome": "automated" if result.get("ok") else "error"}
        self._audit(actor, tool, "execute", "allow", "ok" if result.get("ok") else "error", subject, detail)
        return {
            "ok": bool(result.get("ok")),
            "status": result.get("status", "ok"),
            "executed": bool(result.get("ok")),
            "effect": "allow",
            "result": result,
        }

    def _authorize(
        self,
        tool: str,
        actor: str,
        subject: str,
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        missing = self._missing_scopes(tool)
        if missing:
            self._audit(
                actor,
                tool,
                "deny",
                "deny",
                "scope_not_granted",
                subject,
                {"missing_scopes": missing},
            )
            return {
                "ok": False,
                "status": "scope_not_granted",
                "executed": False,
                "effect": "deny",
                "missing_scopes": missing,
                "message": "This action is outside the scopes configured for this process.",
            }
        decision = self.policy.evaluate(tool, params)
        if decision.effect == "deny":
            self._audit(actor, tool, "deny", "deny", "denied", subject, {"reason": decision.reason})
            return {
                "ok": False,
                "status": "denied",
                "executed": False,
                "effect": "deny",
                "message": decision.reason,
            }
        if decision.effect == "needs_approval":
            approval_id = new_id("apr")
            self.store.create_approval(
                {
                    "id": approval_id,
                    "tool": tool,
                    "requester": actor,
                    "subject_email": subject,
                    "params": params,
                    "status": "pending",
                    "created_at": utc_now(),
                }
            )
            self._audit(
                actor,
                tool,
                "request",
                "needs_approval",
                "pending_approval",
                subject,
                {
                    "required_roles": list(decision.required_roles),
                    "required_count": decision.required_count,
                    "identity_verification": decision.identity_verification,
                    "reason": decision.reason,
                },
                approval_id=approval_id,
            )
            return {
                "ok": True,
                "status": "pending_approval",
                "executed": False,
                "effect": "needs_approval",
                "approval_id": approval_id,
                "required_roles": list(decision.required_roles),
                "required_count": decision.required_count,
                "identity_verification": decision.identity_verification,
                "message": f"{decision.reason} The change has not been made.",
            }
        if decision.classification in {"write", "destructive"}:
            self._audit(actor, tool, "approval", "allow", "not_required", subject)
        return None

    def _dispatch(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            if tool == "run_joiner":
                return self._joiner(params)
            if tool == "run_mover":
                return self._mover(params)
            if tool == "run_leaver":
                return self._leaver(params)
            if tool == "request_group_access":
                return self._grant_group(params)
            if tool == "reset_mfa":
                return self._reset_mfa(params)
            if tool == "suspend_user":
                return self._suspend(params)
        except (KeyError, OktaLiveError) as exc:
            return {"ok": False, "status": "error", "message": str(exc)[:200]}
        return {"ok": False, "status": "error", "message": "No executor for that tool."}

    def _joiner(self, params: dict[str, Any]) -> dict[str, Any]:
        email = params["email"]
        department = params["department"]
        title = params["title"]
        hr = self.store.get_hr(email)
        if hr is None:
            return {"ok": False, "status": "not_in_hr_feed"}
        desired = [name for name in groups_for(department, title) if not name.startswith("phi-")]
        existing = self.okta.get_user(email)
        if (
            existing
            and existing.get("status") == "active"
            and existing.get("department") == department
            and existing.get("title") == title
            and set(desired).issubset(set(self.okta.list_groups(email)))
        ):
            return {
                "ok": True,
                "status": "already_provisioned",
                "email": email,
                "groups": self.okta.list_groups(email),
            }
        profile = {
            "email": email,
            "first_name": hr["first_name"],
            "last_name": hr["last_name"],
            "department": department,
            "title": title,
            "manager_email": hr.get("manager_email") or "",
        }
        self.okta.provision_user(profile)
        self._sync_groups(email, desired, keep_phi=False)
        self.gws.ensure_user(profile)
        self.gws.remove_all_groups(email)
        for name in desired:
            self.gws.add_to_group(email, name)
        self.devices.ensure_pending(email)
        self.store.update_hr_status(email, "active", department, title)
        return {"ok": True, "status": "provisioned", "email": email, "groups": desired, "phi_assigned": False}

    def _mover(self, params: dict[str, Any]) -> dict[str, Any]:
        email = params["email"]
        department = params["department"]
        title = params["title"]
        desired = [name for name in groups_for(department, title) if not name.startswith("phi-")]
        self.okta.update_user(email, department, title)
        self._sync_groups(email, desired, keep_phi=True)
        self.gws.update_user(email, department, title)
        self.gws.remove_all_groups(email)
        for name in desired:
            self.gws.add_to_group(email, name)
        self.store.update_hr_status(email, "active", department, title)
        return {"ok": True, "status": "moved", "email": email, "groups": self.okta.list_groups(email)}

    def _leaver(self, params: dict[str, Any]) -> dict[str, Any]:
        email = params["email"]
        user = self.okta.get_user(email)
        if user is None:
            return {"ok": False, "status": "not_found"}
        if user.get("status") == "deprovisioned":
            return {"ok": True, "status": "already_deprovisioned", "email": email}
        manager = user.get("manager_email") or ""
        if not manager:
            hr = self.store.get_hr(email) or {}
            manager = hr.get("manager_email") or ""
        self.okta.clear_sessions(email)
        removed = self.okta.remove_all_groups(email)
        self.okta.deactivate(email)
        drive = None
        if self.gws.get_user(email) is not None:
            self.gws.remove_all_groups(email)
            if manager and manager != email:
                drive = self.gws.transfer_drive(email, manager)
            self.gws.suspend_user(email)
        released = self.devices.release(email)
        hr = self.store.get_hr(email)
        if hr is not None:
            self.store.update_hr_status(email, "departed", hr["department"], hr["title"])
        return {
            "ok": True,
            "status": "deprovisioned",
            "email": email,
            "groups_removed": removed,
            "sessions_cleared": True,
            "google_status": "suspended",
            "drive": drive,
            "devices_released": released,
            "notification": "MOCK not sent",
        }

    def _grant_group(self, params: dict[str, Any]) -> dict[str, Any]:
        email = params["email"]
        group = params["group"]
        self.okta.add_to_group(email, group)
        if not group.startswith("phi-"):
            self.gws.add_to_group(email, group)
        return {"ok": True, "status": "granted", "email": email, "group": group}

    def _reset_mfa(self, params: dict[str, Any]) -> dict[str, Any]:
        result = self.okta.reset_mfa(params["email"])
        return {"ok": True, "status": "factors_reset", **result}

    def _suspend(self, params: dict[str, Any]) -> dict[str, Any]:
        email = params["email"]
        self.okta.clear_sessions(email)
        self.okta.suspend(email)
        return {"ok": True, "status": "suspended", "email": email, "sessions_cleared": True}

    def _sync_groups(self, email: str, desired: list[str], *, keep_phi: bool) -> None:
        current = self.okta.list_groups(email)
        keep = set(desired)
        if keep_phi:
            keep.update(name for name in current if name.startswith("phi-"))
        remove = [name for name in current if name not in keep and _managed(name)]
        if remove:
            self.okta.remove_groups(email, remove)
        for name in desired:
            if name not in current:
                self.okta.add_to_group(email, name)

    def _satisfied(self, decisions: list[dict[str, Any]], policy: Decision) -> bool:
        if any(row["decision"] == "deny" for row in decisions):
            return False
        approved = [row for row in decisions if row["decision"] == "approve"]
        people = {row["approver"] for row in approved}
        if len(people) < policy.required_count:
            return False
        if policy.distinct_roles and not set(policy.required_roles).issubset({row["role"] for row in approved}):
            return False
        if policy.identity_verification:
            verified = [
                row
                for row in approved
                if row["identity_verified"] and row["verification_method"] in IDENTITY_VERIFICATION_METHODS
            ]
            if not verified:
                return False
        return True

    def _missing_scopes(self, tool: str) -> list[str]:
        required = set(self.policy.scopes_for(tool))
        return sorted(required - set(self.settings.granted_scopes))

    def _safe_user(self, email: str) -> dict[str, Any] | None:
        try:
            return self.okta.get_user(email)
        except OktaLiveError:
            return None

    def _invalid(self, tool: str, actor: str, message: str, subject: str = "") -> dict[str, Any]:
        self._audit(actor, tool, "reject", "deny", "invalid_request", subject, {"message": message})
        return {"ok": False, "status": "invalid_request", "executed": False, "message": message}

    def _reject_decision(self, approval: dict[str, Any], approver: str, message: str) -> dict[str, Any]:
        self._audit(
            approver,
            approval["tool"],
            "decide",
            "deny",
            "rejected",
            approval.get("subject_email") or "",
            {"message": message},
            approval_id=approval["id"],
            approver=approver,
        )
        return {"ok": False, "status": "rejected", "executed": False, "message": message}

    def _audit(
        self,
        actor: str,
        tool: str,
        phase: str,
        effect: str,
        result: str,
        subject: str,
        detail: dict[str, Any] | None = None,
        *,
        approval_id: str = "",
        approver: str = "",
        ts: str | None = None,
    ) -> None:
        self.audit.append(
            actor=actor,
            tool=tool,
            phase=phase,
            effect=effect,
            result=result,
            subject=subject,
            approval_id=approval_id,
            approver=approver,
            detail=detail,
            ts=ts,
        )


def _managed(name: str) -> bool:
    return name.startswith(("dept-", "role-", "app-", "phi-"))


def _public_result(result: dict[str, Any]) -> dict[str, Any]:
    hidden = {"message"}
    return {key: value for key, value in result.items() if key not in hidden}
