from __future__ import annotations

import json
from typing import Any

from mcp_server.tools.spec import ToolSpec


def _build(service: Any, actor: str):
    async def run_leaver(email: str) -> str:
        """Ask to deprovision a person. Does not remove access."""
        return json.dumps(service.run_leaver(email=email, actor=actor))

    return run_leaver


SPEC = ToolSpec(
    name="run_leaver",
    description=(
        "Ask to deprovision a person who is in the HR feed and the directory. "
        "On success the status is pending_approval. Sessions, groups, Google, and "
        "devices are unchanged until a person approves outside this model."
    ),
    scopes=("okta.users.manage", "okta.groups.manage", "okta.sessions.manage"),
    build=_build,
    destructive=True,
    idempotent=True,
)
