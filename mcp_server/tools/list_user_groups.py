from __future__ import annotations

import json
from typing import Any

from mcp_server.tools.spec import ToolSpec


def _build(service: Any, actor: str):
    async def list_user_groups(email: str) -> str:
        """List catalog groups for one user."""
        return json.dumps(service.list_user_groups(email=email, actor=actor))

    return list_user_groups


SPEC = ToolSpec(
    name="list_user_groups",
    description="List lab catalog groups for one user. Read only.",
    scopes=("okta.users.read", "okta.groups.read"),
    build=_build,
    read_only=True,
    idempotent=True,
)
