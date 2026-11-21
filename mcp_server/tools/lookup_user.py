from __future__ import annotations

import json
from typing import Any

from mcp_server.tools.spec import ToolSpec


def _build(service: Any, actor: str):
    async def lookup_user(email: str) -> str:
        """Look up one directory user. Returns allow-listed fields only."""
        return json.dumps(service.lookup_user(email=email, actor=actor))

    return lookup_user


SPEC = ToolSpec(
    name="lookup_user",
    description=(
        "Look up one synthetic directory user by email. Returns allow-listed fields only. "
        "Does not return secrets, tokens, or health data."
    ),
    scopes=("okta.users.read",),
    build=_build,
    read_only=True,
    idempotent=True,
)
