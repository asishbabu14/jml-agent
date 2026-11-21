from __future__ import annotations

import re
from pathlib import Path

from mcp_server.catalog import GROUP_NAMES

REPO = Path(__file__).resolve().parents[1]


def test_env_example_has_empty_values() -> None:
    for line in (REPO / ".env.example").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        _, value = line.split("=", 1)
        assert value.strip() == ""


def test_no_private_key_material_is_committed() -> None:
    blocked_suffixes = {".pem", ".key"}
    skip = {".git", ".terraform", ".venv", "var", "__pycache__", ".pytest_cache", ".ruff_cache"}
    private_header = "-----BEGIN " + "PRIVATE KEY-----"
    rsa_header = "-----BEGIN RSA " + "PRIVATE KEY-----"
    for path in REPO.rglob("*"):
        if not path.is_file() or any(part in skip for part in path.parts):
            continue
        assert path.suffix not in blocked_suffixes
        if path.stat().st_size > 1_000_000:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert private_header not in text
        assert rsa_header not in text


def test_terraform_groups_match_the_catalog() -> None:
    text = (REPO / "terraform" / "okta" / "groups.tf").read_text(encoding="utf-8")
    found = set(re.findall(r'name\s+=\s+"((?:dept|role|app|phi)-[^"]+)"', text))
    assert found == set(GROUP_NAMES)


def test_readme_states_the_lab_limits() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8").lower()
    assert "personal lab" in readme
    assert "synthetic" in readme
    assert "not production" in readme
    assert "employer" in readme


def test_workflow_does_not_apply_terraform() -> None:
    text = (REPO / ".github" / "workflows" / "terraform.yml").read_text(encoding="utf-8")
    assert "terraform plan" in text
    assert "terraform validate" in text
    for line in text.splitlines():
        stripped = line.strip()
        assert not stripped.startswith("terraform apply")
        assert "run: terraform apply" not in stripped
