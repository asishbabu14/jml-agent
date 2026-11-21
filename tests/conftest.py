from __future__ import annotations

from pathlib import Path

import pytest
from mcp_server.config import Settings
from mcp_server.factory import build_service
from mcp_server.service import ITOpsService

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def service(tmp_path: Path) -> ITOpsService:
    return build_service(Settings.for_lab(tmp_path))
