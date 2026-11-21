"""Process settings. Live Okta is opt-in and fails closed on a partial config."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mcp_server.catalog import LIVE_DEFAULT_SCOPES, MOCK_GRANTED_SCOPES

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent


class ConfigError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def runbook_dir() -> Path:
    override = os.environ.get("JML_RUNBOOK_DIR", "").strip()
    if override:
        return Path(override)
    candidate = REPO_ROOT / "runbooks"
    if candidate.is_dir():
        return candidate
    return PACKAGE_ROOT / "runbooks"


def default_hr_csv() -> Path:
    return REPO_ROOT / "hris_mock" / "employees.csv"


def default_devices() -> Path:
    return PACKAGE_ROOT / "fixtures" / "devices.json"


def default_policy() -> Path:
    return PACKAGE_ROOT / "policy" / "policy.yaml"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    actor: str
    runbook_dir: Path
    hr_csv: Path
    devices_path: Path
    policy_path: Path
    granted_scopes: frozenset[str]
    okta_org_url: str | None = None
    okta_client_id: str | None = None
    okta_private_key_path: str | None = None
    live_okta: bool = False

    @classmethod
    def for_lab(
        cls,
        data_dir: Path,
        *,
        scopes: frozenset[str] | None = None,
        actor: str = "it-agent@lab.example",
    ) -> Settings:
        """Mock lab settings that ignore the process environment."""
        return cls(
            data_dir=data_dir,
            actor=actor,
            runbook_dir=runbook_dir(),
            hr_csv=default_hr_csv(),
            devices_path=default_devices(),
            policy_path=default_policy(),
            granted_scopes=scopes if scopes is not None else MOCK_GRANTED_SCOPES,
            live_okta=False,
        )

    @classmethod
    def from_env(cls) -> Settings:
        org = _blank(os.environ.get("OKTA_ORG_URL"))
        client_id = _blank(os.environ.get("OKTA_CLIENT_ID"))
        key_path = _blank(os.environ.get("OKTA_PRIVATE_KEY_PATH"))
        requested = [bool(org), bool(client_id), bool(key_path)]
        if any(requested) and not all(requested):
            raise ConfigError(
                "Set OKTA_ORG_URL, OKTA_CLIENT_ID, and OKTA_PRIVATE_KEY_PATH together, "
                "or leave all three empty to stay on the MOCK Okta adapter."
            )
        live = all(requested)
        if live:
            key_file = Path(key_path or "")
            if not key_file.is_file():
                raise ConfigError(
                    "OKTA_PRIVATE_KEY_PATH does not point at a readable key file. "
                    "Refusing to start a half-configured live adapter."
                )
        scopes = _parse_scopes(os.environ.get("OKTA_SCOPES"))
        if scopes is None:
            scopes = LIVE_DEFAULT_SCOPES if live else MOCK_GRANTED_SCOPES
        data_dir = Path(_blank(os.environ.get("JML_DATA_DIR")) or "var/agent")
        actor = _blank(os.environ.get("JML_ACTOR")) or "it-agent@lab.example"
        return cls(
            data_dir=data_dir,
            actor=actor,
            runbook_dir=runbook_dir(),
            hr_csv=default_hr_csv(),
            devices_path=default_devices(),
            policy_path=default_policy(),
            granted_scopes=scopes,
            okta_org_url=org.rstrip("/") if org else None,
            okta_client_id=client_id,
            okta_private_key_path=key_path,
            live_okta=live,
        )


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_scopes(value: str | None) -> frozenset[str] | None:
    if value is None or not value.strip():
        return None
    parts = value.replace(",", " ").split()
    return frozenset(parts)
