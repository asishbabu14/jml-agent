"""Directory objects the lab is allowed to touch.

Names here match terraform/okta/groups.tf. A test fails if they drift.
phi-* groups are labels for the approval rule. They hold no health data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Group:
    name: str
    description: str
    owner_email: str


GROUPS: tuple[Group, ...] = (
    Group("dept-engineering", "Department: Engineering. Synthetic lab.", "morgan.lee@lab.example"),
    Group(
        "dept-clinical-ops",
        "Department label only. No patient or member data.",
        "morgan.lee@lab.example",
    ),
    Group("dept-it", "Department: IT. Synthetic lab.", "sam.okafor@lab.example"),
    Group("dept-security", "Department: Security. Synthetic lab.", "sam.okafor@lab.example"),
    Group("role-engineer", "Role: engineer. Synthetic lab.", "morgan.lee@lab.example"),
    Group("role-it-support", "Role: IT support. Synthetic lab.", "sam.okafor@lab.example"),
    Group("role-manager", "Role: people manager. Synthetic lab.", "sam.okafor@lab.example"),
    Group("app-slack", "Bookmark app group for the lab Slack tile.", "morgan.lee@lab.example"),
    Group("app-notion", "Bookmark app group for the lab Notion tile.", "morgan.lee@lab.example"),
    Group(
        "phi-access",
        "LABEL ONLY. Not a store of PHI. Never assigned by a group rule.",
        "sam.okafor@lab.example",
    ),
)

GROUP_NAMES: frozenset[str] = frozenset(group.name for group in GROUPS)

DEPT_GROUPS: dict[str, str] = {
    "Engineering": "dept-engineering",
    "Clinical Operations": "dept-clinical-ops",
    "IT": "dept-it",
    "Security": "dept-security",
}

KNOWN_DEPARTMENTS: frozenset[str] = frozenset(DEPT_GROUPS)

# Scopes the mock lab grants so the scripted demo can run.
# A live Okta process does not receive this set unless OKTA_SCOPES says so.
MOCK_GRANTED_SCOPES: frozenset[str] = frozenset(
    {
        "okta.users.read",
        "okta.groups.read",
        "okta.users.manage",
        "okta.groups.manage",
        "okta.sessions.manage",
    }
)

LIVE_DEFAULT_SCOPES: frozenset[str] = frozenset({"okta.users.read", "okta.groups.read"})

TICKET_OWNERS: dict[str, str] = {
    "access": "it-access",
    "mfa": "it-identity",
    "joiner": "it-lifecycle",
    "mover": "it-lifecycle",
    "leaver": "it-lifecycle",
    "device": "it-endpoint",
    "how_to": "it-support",
    "other": "it-support",
}

TICKET_CATEGORIES: frozenset[str] = frozenset(TICKET_OWNERS)
TICKET_URGENCIES: frozenset[str] = frozenset({"low", "normal", "high"})

IDENTITY_VERIFICATION_METHODS: frozenset[str] = frozenset({"video", "in_person", "manager_callback"})

JML_TOOLS: frozenset[str] = frozenset(
    {
        "request_group_access",
        "reset_mfa",
        "run_joiner",
        "run_mover",
        "run_leaver",
        "suspend_user",
    }
)


def groups_for(department: str, title: str) -> list[str]:
    """Groups a joiner or mover receives. phi-* is never included."""
    names: list[str] = ["app-slack"]
    department_group = DEPT_GROUPS.get(department)
    if department_group:
        names.append(department_group)
    title_l = title.lower()
    if "manager" in title_l:
        names.append("role-manager")
    elif "engineer" in title_l:
        names.append("role-engineer")
    elif department == "IT":
        names.append("role-it-support")
    if department in {"Engineering", "IT", "Security"}:
        names.append("app-notion")
    return names
