from __future__ import annotations

import json
from typing import Any

from mcp_server.tools.spec import ToolSpec


def _build(service: Any, actor: str):
    async def suspend_user(email: str) -> str:
        """Ask to suspend a person. Does not suspend them."""
        return json.dumps(service.suspend_user(email=email, actor=actor))

    return suspend_user


SPEC = ToolSpec(
    name="suspend_user",
    description=(
        "Ask to suspend an account and clear sessions. On success the status is "
        "pending_approval. IT and security must both approve. You cannot approve this."
    ),
    scopes=("okta.users.manage", "okta.sessions.manage"),
    build=_build,
    destructive=True,
    idempotent=True,
)
