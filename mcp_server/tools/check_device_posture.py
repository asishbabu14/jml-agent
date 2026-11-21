from __future__ import annotations

import json
from typing import Any

from mcp_server.tools.spec import ToolSpec


def _build(service: Any, actor: str):
    async def check_device_posture(email: str) -> str:
        """Read MOCK device posture for one person."""
        return json.dumps(service.check_device_posture(email=email, actor=actor))

    return check_device_posture


SPEC = ToolSpec(
    name="check_device_posture",
    description=(
        "Read device posture from the MOCK Iru-style inventory. "
        "This is not a live MDM or SentinelOne connection."
    ),
    scopes=(),
    build=_build,
    read_only=True,
    idempotent=True,
)
