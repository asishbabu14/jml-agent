from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp_server.config import Settings
from mcp_server.factory import build_service
from mcp_server.server import build_server, run


def test_check_command_reports_mock(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_CLIENT_ID", raising=False)
    monkeypatch.delenv("OKTA_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.setenv("JML_DATA_DIR", str(tmp_path))
    assert run(["--check"]) == 0


def test_in_process_tool_call_returns_a_user(tmp_path: Path) -> None:
    service = build_service(Settings.for_lab(tmp_path))
    server = build_server(service)

    async def call() -> str:
        result = await server.call_tool(
            "lookup_user",
            {"email": "casey.nguyen@lab.example"},
        )
        text = result.content[0].text
        assert isinstance(text, str)
        return text

    payload = json.loads(asyncio.run(call()))
    assert payload["user"]["display_name"] == "Casey Nguyen"
    assert payload["effect"] == "allow"


def test_stdio_server_starts_in_mock_mode(tmp_path: Path) -> None:
    async def session() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
            env={"JML_DATA_DIR": str(tmp_path), "PYTHONUNBUFFERED": "1"},
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                init = await client.initialize()
                assert init.server_info.name == "jml-agent"
                listed = await client.list_tools()
                names = {tool.name for tool in listed.tools}
                assert "lookup_user" in names
                assert "run_leaver" in names
                assert "decide_approval" not in names
                result = await client.call_tool(
                    "lookup_user",
                    {"email": "morgan.lee@lab.example"},
                )
                assert result.is_error is False
                body = json.loads(result.content[0].text)
                assert body["user"]["department"] == "Engineering"

    asyncio.run(session())
    assert "OKTA_ORG_URL" not in os.environ or os.environ.get("OKTA_ORG_URL", "") == ""
