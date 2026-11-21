"""Evaluate policy.yaml. Callers do not infer effect from free text."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Decision:
    effect: str
    reason: str
    required_roles: tuple[str, ...] = ()
    required_count: int = 0
    distinct_roles: bool = False
    distinct_approvers: bool = False
    identity_verification: bool = False
    classification: str = "read"


@dataclass
class PolicyEngine:
    default_effect: str
    roles: dict[str, frozenset[str]]
    tools: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> PolicyEngine:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        roles = {
            name: frozenset(email.strip().lower() for email in members)
            for name, members in (raw.get("approver_roles") or {}).items()
        }
        return cls(
            default_effect=str(raw.get("default_effect", "deny")),
            roles=roles,
            tools=dict(raw.get("tools") or {}),
        )

    def scopes_for(self, tool: str) -> tuple[str, ...]:
        spec = self.tools.get(tool) or {}
        return tuple(spec.get("okta_scopes") or ())

    def classification(self, tool: str) -> str:
        spec = self.tools.get(tool) or {}
        return str(spec.get("classification", "read"))

    def role_members(self, role: str) -> frozenset[str]:
        return self.roles.get(role, frozenset())

    def evaluate(self, tool: str, params: dict[str, Any]) -> Decision:
        spec = self.tools.get(tool)
        if spec is None:
            return Decision(
                effect="deny",
                reason="That tool is not in policy.yaml.",
                classification="read",
            )
        chosen = spec
        for constraint in spec.get("constraints") or []:
            if _matches(constraint.get("when") or {}, params):
                chosen = {**spec, **constraint, "approval": _approval_block(spec, constraint)}
                break
        effect = str(chosen.get("effect", self.default_effect))
        reason = str(chosen.get("reason") or "Policy decision applied.")
        classification = str(spec.get("classification", "read"))
        if effect == "allow":
            return Decision(effect="allow", reason=reason, classification=classification)
        if effect == "deny":
            return Decision(effect="deny", reason=reason, classification=classification)
        approval = chosen.get("approval") or {}
        roles = tuple(approval.get("roles") or [])
        count = int(approval.get("count") or len(roles) or 1)
        return Decision(
            effect="needs_approval",
            reason=reason,
            required_roles=roles,
            required_count=count,
            distinct_roles=bool(approval.get("distinct_roles")),
            distinct_approvers=bool(approval.get("distinct_approvers", count > 1)),
            identity_verification=bool(approval.get("identity_verification")),
            classification=classification,
        )


def _approval_block(spec: dict[str, Any], constraint: dict[str, Any]) -> dict[str, Any]:
    base = dict(spec.get("approval") or {})
    for key in ("roles", "count", "distinct_roles", "distinct_approvers", "identity_verification"):
        if key in constraint:
            base[key] = constraint[key]
    return base


def _matches(when: dict[str, Any], params: dict[str, Any]) -> bool:
    if not when:
        return False
    prefix = when.get("group_prefix")
    if prefix is not None and not str(params.get("group", "")).startswith(str(prefix)):
        return False
    return True
