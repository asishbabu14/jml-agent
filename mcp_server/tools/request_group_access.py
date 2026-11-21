from __future__ import annotations

import json
from typing import Any

from mcp_server.tools.spec import ToolSpec


def _build(service: Any, actor: str):
    async def request_group_access(email: str, group: str, reason: str) -> str:
        """Request a catalog group. Does not grant it."""
        return json.dumps(
            service.request_group_access(email=email, group=group, reason=reason, actor=actor)
        )

    return request_group_access


SPEC = ToolSpec(
    name="request_group_access",
    description=(
        "Ask to add a catalog group. On success the status is pending_approval and the "
        "group is not added. phi-* groups need both a manager and a security partner. "
        "You cannot approve this request."
    ),
    scopes=("okta.groups.manage",),
    build=_build,
    idempotent=True,
)
