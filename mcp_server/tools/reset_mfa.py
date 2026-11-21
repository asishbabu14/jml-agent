from __future__ import annotations

import json
from typing import Any

from mcp_server.tools.spec import ToolSpec


def _build(service: Any, actor: str):
    async def reset_mfa(email: str) -> str:
        """Ask to reset MFA. Does not reset it."""
        return json.dumps(service.reset_mfa(email=email, actor=actor))

    return reset_mfa


SPEC = ToolSpec(
    name="reset_mfa",
    description=(
        "Ask to reset MFA factors. On success the status is pending_approval and factors "
        "are unchanged. Identity verification is recorded by the human approver, not by you."
    ),
    scopes=("okta.users.manage",),
    build=_build,
    idempotent=True,
)
