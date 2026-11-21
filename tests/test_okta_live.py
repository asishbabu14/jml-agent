from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from mcp_server.adapters.okta_live import ASSERTION_TYPE, OktaLiveAdapter
from mcp_server.catalog import LIVE_DEFAULT_SCOPES


def _pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")


def test_token_request_uses_private_key_jwt_not_ssws() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/oauth2/v1/token":
            return httpx.Response(
                200,
                json={"access_token": "test-token", "expires_in": 3600, "token_type": "Bearer"},
            )
        if request.url.path == "/api/v1/users/casey.nguyen@lab.example":
            return httpx.Response(
                200,
                json={
                    "id": "00uLAB",
                    "status": "ACTIVE",
                    "profile": {
                        "email": "casey.nguyen@lab.example",
                        "firstName": "Casey",
                        "lastName": "Nguyen",
                        "department": "Engineering",
                        "title": "Software Engineer",
                    },
                },
            )
        return httpx.Response(404, json={})

    pem = _pem()
    adapter = OktaLiveAdapter(
        "https://lab.okta.com",
        "client-lab",
        pem,
        LIVE_DEFAULT_SCOPES,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    user = adapter.get_user("casey.nguyen@lab.example")
    assert user is not None
    assert user["email"] == "casey.nguyen@lab.example"
    assert adapter.backend_label == "okta-api"
    token_call = seen[0]
    form = parse_qs(token_call.content.decode())
    assert form["grant_type"] == ["client_credentials"]
    assert form["client_assertion_type"] == [ASSERTION_TYPE]
    assert "api_token" not in form
    assert "ssws" not in {key.lower() for key in form}
    claims = jwt.decode(form["client_assertion"][0], options={"verify_signature": False})
    assert claims["iss"] == "client-lab"
    assert claims["sub"] == "client-lab"
    assert claims["aud"] == "https://lab.okta.com/oauth2/v1/token"
    assert token_call.headers.get("authorization") is None
    user_call = seen[1]
    assert user_call.headers["authorization"] == "Bearer test-token"


def test_factory_selects_live_adapter_without_calling_okta(tmp_path: Path, monkeypatch) -> None:
    key = tmp_path / "okta.pem"
    key.write_text(_pem(), encoding="utf-8")
    monkeypatch.setenv("OKTA_ORG_URL", "https://lab.okta.com")
    monkeypatch.setenv("OKTA_CLIENT_ID", "client-lab")
    monkeypatch.setenv("OKTA_PRIVATE_KEY_PATH", str(key))
    monkeypatch.setenv("JML_DATA_DIR", str(tmp_path / "data"))
    from mcp_server.config import Settings
    from mcp_server.factory import build_service

    service = build_service(Settings.from_env())
    assert service.okta.backend_name == "OktaLiveAdapter"
    assert service.gws.backend_label == "MOCK"
    assert service.devices.backend_label == "MOCK"
