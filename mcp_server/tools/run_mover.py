from __future__ import annotations

import json
from typing import Any

from mcp_server.tools.spec import ToolSpec


def _build(service: Any, actor: str):
    async def run_mover(email: str, department: str, title: str) -> str:
        """Ask to change department and title. Does not change them."""
        return json.dumps(
            service.run_mover(email=email, department=department, title=title, actor=actor)
        )

    return run_mover


SPEC = ToolSpec(
    name="run_mover",
    description=(
        "Ask to move a person to a new department and title. "
        "On success the status is pending_approval and groups are unchanged. "
        "You cannot approve or execute this request."
    ),
    scopes=("okta.users.manage", "okta.groups.manage"),
    build=_build,
    idempotent=True,
)
