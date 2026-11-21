from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mcp_server.catalog import LIVE_DEFAULT_SCOPES
from mcp_server.config import ConfigError, Settings
from mcp_server.factory import build_service
from mcp_server.server import build_server


def test_read_only_scopes_block_writes(tmp_path: Path) -> None:
    service = build_service(Settings.for_lab(tmp_path, scopes=LIVE_DEFAULT_SCOPES))
    looked_up = service.lookup_user("casey.nguyen@lab.example", actor="it-agent@lab.example")
    assert looked_up["status"] == "ok"
    blocked = service.reset_mfa("casey.nguyen@lab.example", actor="it-agent@lab.example")
    assert blocked["status"] == "scope_not_granted"
    assert service.lookup_user("casey.nguyen@lab.example", actor="it-agent@lab.example")["user"]["mfa_enrolled"]


def test_server_omits_tools_the_scopes_do_not_cover(tmp_path: Path) -> None:
    service = build_service(Settings.for_lab(tmp_path, scopes=LIVE_DEFAULT_SCOPES))
    server = build_server(service)
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert "lookup_user" in names
    assert "search_runbooks" in names
    assert "reset_mfa" not in names
    assert "run_joiner" not in names
    assert "decide_approval" not in names
    assert "execute" not in names


def test_partial_okta_env_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OKTA_ORG_URL", "https://example.okta.com")
    monkeypatch.delenv("OKTA_CLIENT_ID", raising=False)
    monkeypatch.delenv("OKTA_PRIVATE_KEY_PATH", raising=False)
    with pytest.raises(ConfigError):
        Settings.from_env()


def test_empty_okta_env_stays_on_mock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_CLIENT_ID", raising=False)
    monkeypatch.delenv("OKTA_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.setenv("JML_DATA_DIR", str(tmp_path))
    settings = Settings.from_env()
    assert settings.live_okta is False
    service = build_service(settings)
    assert service.okta.backend_label == "MOCK"
