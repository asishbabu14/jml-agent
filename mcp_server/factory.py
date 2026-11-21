"""Wire the process. Live Okta is used only when settings say the config is complete."""

from __future__ import annotations

from mcp_server.adapters.gws_mock import GoogleWorkspaceMock
from mcp_server.adapters.mdm_mock import DeviceInventoryMock
from mcp_server.adapters.okta_live import OktaLiveAdapter
from mcp_server.adapters.okta_mock import OktaMockAdapter
from mcp_server.adapters.tickets import TicketStore
from mcp_server.audit.log import AuditLog
from mcp_server.config import Settings
from mcp_server.policy.engine import PolicyEngine
from mcp_server.seed import seed
from mcp_server.service import ITOpsService
from mcp_server.store import Store


def build_service(settings: Settings) -> ITOpsService:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(settings.data_dir / "jml.db")
    seed(store, settings.hr_csv, settings.devices_path)
    if settings.live_okta:
        okta: OktaMockAdapter | OktaLiveAdapter = OktaLiveAdapter.from_key_file(
            settings.okta_org_url or "",
            settings.okta_client_id or "",
            settings.okta_private_key_path or "",
            settings.granted_scopes,
        )
    else:
        okta = OktaMockAdapter(store)
    return ITOpsService(
        settings=settings,
        store=store,
        policy=PolicyEngine.load(settings.policy_path),
        audit=AuditLog(settings.data_dir / "audit.jsonl"),
        okta=okta,
        gws=GoogleWorkspaceMock(store),
        devices=DeviceInventoryMock(store),
        tickets=TicketStore(store),
    )
