"""Google Workspace port.

The lab ships a MOCK implementation in gws_mock.py. There is no live Workspace
client here: a Workspace tenant is not assumed. GAM commands that match the
mock methods are listed beside them so an operator can see the real equivalent.

    ensure / update user     gam create user <email> firstname .. lastname ..
    suspend                  gam update user <email> suspended on
    transfer drive           gam user <email> transfer drive <manager>
    add to group             gam update group <group> add member <email>
    remove from groups       gam update group <group> remove member <email>
"""

from __future__ import annotations

from mcp_server.adapters.base import WorkspaceAdapter

__all__ = ["WorkspaceAdapter"]
