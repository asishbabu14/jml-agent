from __future__ import annotations

from mcp_server.service import ITOpsService

AGENT = "it-agent@lab.example"
IT = "morgan.lee@lab.example"
SECURITY = "sam.okafor@lab.example"
OPERATOR = "operator@lab.example"


def test_joiner_waits_for_approval_and_skips_phi(service: ITOpsService) -> None:
    requested = service.run_joiner(
        "jordan.kim@lab.example", "Engineering", "Software Engineer", actor=AGENT
    )
    assert requested["status"] == "pending_approval"
    assert requested["executed"] is False
    assert service.lookup_user("jordan.kim@lab.example", actor=AGENT)["status"] == "not_found"

    decided = service.decide(requested["approval_id"], IT, "approve", "it")
    assert decided["status"] == "approved"
    done = service.execute(requested["approval_id"], actor=OPERATOR)
    assert done["executed"] is True
    groups = service.list_user_groups("jordan.kim@lab.example", actor=AGENT)["groups"]
    assert "dept-engineering" in groups
    assert "role-engineer" in groups
    assert "phi-access" not in groups
    again = service.execute(requested["approval_id"], actor=OPERATOR)
    assert again["idempotent"] is True


def test_leaver_clears_access(service: ITOpsService) -> None:
    requested = service.run_leaver("taylor.brooks@lab.example", actor=AGENT)
    assert requested["executed"] is False
    service.decide(requested["approval_id"], IT, "approve", "it")
    done = service.execute(requested["approval_id"], actor=OPERATOR)
    assert done["result"]["google_status"] == "suspended"
    assert done["result"]["drive"]["drive_transferred_to"] == "sam.okafor@lab.example"
    assert done["result"]["sessions_cleared"] is True
    user = service.lookup_user("taylor.brooks@lab.example", actor=AGENT)["user"]
    assert user["status"] == "deprovisioned"
    assert service.list_user_groups("taylor.brooks@lab.example", actor=AGENT)["groups"] == []
    devices = service.check_device_posture("taylor.brooks@lab.example", actor=AGENT)["devices"]
    assert devices[0]["assignment_status"] == "pending_retrieval"


def test_mover_swaps_department_group(service: ITOpsService) -> None:
    before = service.list_user_groups("quinn.diaz@lab.example", actor=AGENT)["groups"]
    assert "dept-clinical-ops" in before
    requested = service.run_mover(
        "quinn.diaz@lab.example", "Engineering", "Software Engineer", actor=AGENT
    )
    service.decide(requested["approval_id"], IT, "approve", "it")
    service.execute(requested["approval_id"], actor=OPERATOR)
    groups = service.list_user_groups("quinn.diaz@lab.example", actor=AGENT)["groups"]
    assert "dept-engineering" in groups
    assert "role-engineer" in groups
    assert "dept-clinical-ops" not in groups


def test_requester_cannot_approve(service: ITOpsService) -> None:
    requested = service.run_joiner(
        "jordan.kim@lab.example", "Engineering", "Software Engineer", actor=IT
    )
    rejected = service.decide(requested["approval_id"], IT, "approve", "it")
    assert rejected["status"] == "rejected"
    assert service.lookup_user("jordan.kim@lab.example", actor=AGENT)["status"] == "not_found"


def test_mfa_reset_needs_identity_check(service: ITOpsService) -> None:
    requested = service.reset_mfa("casey.nguyen@lab.example", actor=AGENT)
    rejected = service.decide(requested["approval_id"], IT, "approve", "it")
    assert rejected["status"] == "rejected"
    assert service.lookup_user("casey.nguyen@lab.example", actor=AGENT)["user"]["mfa_enrolled"] is True
    approved = service.decide(
        requested["approval_id"],
        IT,
        "approve",
        "it",
        identity_verified=True,
        verification_method="video",
    )
    assert approved["status"] == "approved"
    done = service.execute(requested["approval_id"], actor=OPERATOR)
    assert done["executed"] is True
    assert service.lookup_user("casey.nguyen@lab.example", actor=AGENT)["user"]["mfa_enrolled"] is False


def test_suspend_needs_two_people(service: ITOpsService) -> None:
    requested = service.suspend_user("riley.chen@lab.example", actor=AGENT)
    service.decide(requested["approval_id"], IT, "approve", "it")
    early = service.execute(requested["approval_id"], actor=OPERATOR)
    assert early["executed"] is False
    service.decide(requested["approval_id"], SECURITY, "approve", "security")
    done = service.execute(requested["approval_id"], actor=OPERATOR)
    assert done["executed"] is True
    assert service.lookup_user("riley.chen@lab.example", actor=AGENT)["user"]["status"] == "suspended"


def test_unknown_person_is_not_provisioned(service: ITOpsService) -> None:
    result = service.run_joiner("nobody@lab.example", "Engineering", "Software Engineer", actor=AGENT)
    assert result["status"] == "invalid_request"
    assert "approval_id" not in result


def test_execute_without_approval_does_nothing(service: ITOpsService) -> None:
    requested = service.run_leaver("taylor.brooks@lab.example", actor=AGENT)
    early = service.execute(requested["approval_id"], actor=OPERATOR)
    assert early["status"] == "pending_approval"
    assert service.lookup_user("taylor.brooks@lab.example", actor=AGENT)["user"]["status"] == "active"
