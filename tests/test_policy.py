from __future__ import annotations

from mcp_server.config import default_policy
from mcp_server.policy.engine import PolicyEngine


def test_unknown_tool_is_denied() -> None:
    policy = PolicyEngine.load(default_policy())
    decision = policy.evaluate("delete_everything", {})
    assert decision.effect == "deny"


def test_published_effects() -> None:
    policy = PolicyEngine.load(default_policy())
    expected = {
        "lookup_user": "allow",
        "list_user_groups": "allow",
        "check_device_posture": "allow",
        "search_runbooks": "allow",
        "create_ticket": "allow",
        "request_group_access": "needs_approval",
        "reset_mfa": "needs_approval",
        "run_joiner": "needs_approval",
        "run_mover": "needs_approval",
        "run_leaver": "needs_approval",
        "suspend_user": "needs_approval",
    }
    for tool, effect in expected.items():
        assert policy.evaluate(tool, {"group": "app-wiki"}).effect == effect


def test_phi_group_needs_manager_and_security() -> None:
    policy = PolicyEngine.load(default_policy())
    decision = policy.evaluate("request_group_access", {"group": "phi-access"})
    assert decision.effect == "needs_approval"
    assert decision.required_roles == ("manager", "security")
    assert decision.required_count == 2
    assert decision.distinct_roles is True


def test_suspend_is_two_person() -> None:
    policy = PolicyEngine.load(default_policy())
    decision = policy.evaluate("suspend_user", {"email": "casey.nguyen@lab.example"})
    assert decision.required_roles == ("it", "security")
    assert decision.required_count == 2


def test_mfa_requires_identity_verification() -> None:
    policy = PolicyEngine.load(default_policy())
    decision = policy.evaluate("reset_mfa", {"email": "casey.nguyen@lab.example"})
    assert decision.identity_verification is True
