from __future__ import annotations

import json
from typing import Any

from mcp_server.tools.spec import ToolSpec


def _build(service: Any, actor: str):
    async def run_joiner(email: str, department: str, title: str) -> str:
        """Ask to provision a person from the HR feed. Does not create the account."""
        return json.dumps(
            service.run_joiner(email=email, department=department, title=title, actor=actor)
        )

    return run_joiner


SPEC = ToolSpec(
    name="run_joiner",
    description=(
        "Ask to provision a person who is already in the synthetic HR feed. "
        "On success the status is pending_approval and no account is created. "
        "You cannot approve or execute this request."
    ),
    scopes=("okta.users.manage", "okta.groups.manage"),
    build=_build,
    idempotent=True,
)
