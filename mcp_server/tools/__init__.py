"""Registered MCP tools. Approval and execute stay off this list."""

from mcp_server.tools.check_device_posture import SPEC as check_device_posture
from mcp_server.tools.create_ticket import SPEC as create_ticket
from mcp_server.tools.list_user_groups import SPEC as list_user_groups
from mcp_server.tools.lookup_user import SPEC as lookup_user
from mcp_server.tools.request_group_access import SPEC as request_group_access
from mcp_server.tools.reset_mfa import SPEC as reset_mfa
from mcp_server.tools.run_joiner import SPEC as run_joiner
from mcp_server.tools.run_leaver import SPEC as run_leaver
from mcp_server.tools.run_mover import SPEC as run_mover
from mcp_server.tools.search_runbooks import SPEC as search_runbooks
from mcp_server.tools.spec import ToolSpec
from mcp_server.tools.suspend_user import SPEC as suspend_user

TOOLS: tuple[ToolSpec, ...] = (
    lookup_user,
    list_user_groups,
    check_device_posture,
    search_runbooks,
    create_ticket,
    request_group_access,
    reset_mfa,
    run_joiner,
    run_mover,
    run_leaver,
    suspend_user,
)

__all__ = ["TOOLS", "ToolSpec"]
