"""Live Okta Management API adapter.

Selected only when OKTA_ORG_URL, OKTA_CLIENT_ID, and OKTA_PRIVATE_KEY_PATH are
all set. Authentication is OAuth 2.0 private_key_jwt. This module never reads
an SSWS API token.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import jwt

ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"


class OktaLiveError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class OktaLiveAdapter:
    backend_label = "okta-api"
    backend_name = "OktaLiveAdapter"

    def __init__(
        self,
        org_url: str,
        client_id: str,
        private_key_pem: str,
        scopes: frozenset[str],
        client: httpx.Client | None = None,
    ) -> None:
        self.org_url = org_url.rstrip("/")
        self.client_id = client_id
        self.private_key_pem = private_key_pem
        self.scopes = " ".join(sorted(scopes))
        self.client = client or httpx.Client(timeout=15.0, follow_redirects=False)
        self._access_token = ""
        self._token_expiry = 0.0
        self._group_ids: dict[str, str] = {}

    @classmethod
    def from_key_file(
        cls,
        org_url: str,
        client_id: str,
        key_path: str,
        scopes: frozenset[str],
    ) -> OktaLiveAdapter:
        pem = Path(key_path).read_text(encoding="utf-8")
        if "PRIVATE KEY" not in pem:
            raise OktaLiveError("OKTA_PRIVATE_KEY_PATH is not a PEM private key.")
        return cls(org_url, client_id, pem, scopes)

    def get_user(self, email: str) -> dict[str, Any] | None:
        response = self._request("GET", f"/api/v1/users/{quote(email, safe='')}")
        if response.status_code == 404:
            return None
        self._raise_for_status(response)
        return _user_view(response.json())

    def list_groups(self, email: str) -> list[str]:
        user = self.get_user(email)
        if user is None:
            return []
        response = self._request("GET", f"/api/v1/users/{quote(user['id'], safe='')}/groups")
        self._raise_for_status(response)
        return sorted(item["profile"]["name"] for item in response.json())

    def provision_user(self, profile: dict[str, Any]) -> dict[str, Any]:
        body = {
            "profile": {
                "firstName": profile.get("first_name") or "Lab",
                "lastName": profile.get("last_name") or "User",
                "email": profile["email"],
                "login": profile["email"],
                "department": profile.get("department", ""),
                "title": profile.get("title", ""),
            }
        }
        response = self._request("POST", "/api/v1/users", params={"activate": "true"}, json=body)
        self._raise_for_status(response)
        return _user_view(response.json())

    def update_user(self, email: str, department: str, title: str) -> dict[str, Any]:
        user = self._require(email)
        response = self._request(
            "POST",
            f"/api/v1/users/{quote(user['id'], safe='')}",
            json={"profile": {"department": department, "title": title}},
        )
        self._raise_for_status(response)
        return _user_view(response.json())

    def add_to_group(self, email: str, group: str) -> None:
        user = self._require(email)
        group_id = self._group_id(group)
        response = self._request(
            "PUT",
            f"/api/v1/groups/{quote(group_id, safe='')}/users/{quote(user['id'], safe='')}",
        )
        self._raise_for_status(response)

    def remove_groups(self, email: str, groups: list[str]) -> list[str]:
        user = self._require(email)
        removed: list[str] = []
        for name in groups:
            group_id = self._group_id(name)
            response = self._request(
                "DELETE",
                f"/api/v1/groups/{quote(group_id, safe='')}/users/{quote(user['id'], safe='')}",
            )
            if response.status_code not in {204, 404}:
                self._raise_for_status(response)
            removed.append(name)
        return removed

    def remove_all_groups(self, email: str) -> list[str]:
        current = self.list_groups(email)
        # Everyone and built-in groups are not managed here; only catalog names.
        from mcp_server.catalog import GROUP_NAMES

        managed = [name for name in current if name in GROUP_NAMES]
        return self.remove_groups(email, managed)

    def deactivate(self, email: str) -> dict[str, Any]:
        user = self._require(email)
        response = self._request(
            "POST",
            f"/api/v1/users/{quote(user['id'], safe='')}/lifecycle/deactivate",
        )
        self._raise_for_status(response)
        return {"email": email, "status": "deprovisioned"}

    def suspend(self, email: str) -> dict[str, Any]:
        user = self._require(email)
        response = self._request(
            "POST",
            f"/api/v1/users/{quote(user['id'], safe='')}/lifecycle/suspend",
        )
        self._raise_for_status(response)
        return {"email": email, "status": "suspended"}

    def clear_sessions(self, email: str) -> dict[str, Any]:
        user = self._require(email)
        response = self._request(
            "DELETE",
            f"/api/v1/users/{quote(user['id'], safe='')}/sessions",
        )
        if response.status_code not in {204, 404}:
            self._raise_for_status(response)
        return {"email": email, "sessions_cleared": True}

    def reset_mfa(self, email: str) -> dict[str, Any]:
        user = self._require(email)
        response = self._request(
            "POST",
            f"/api/v1/users/{quote(user['id'], safe='')}/lifecycle/reset_factors",
        )
        self._raise_for_status(response)
        return {"email": email, "mfa_enrolled": False}

    def client_assertion(self) -> str:
        now = int(time.time())
        payload = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": f"{self.org_url}/oauth2/v1/token",
            "iat": now,
            "exp": now + 300,
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(payload, self.private_key_pem, algorithm="RS256")
        if isinstance(token, bytes):
            return token.decode("ascii")
        return token

    def _token(self) -> str:
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        response = self.client.post(
            f"{self.org_url}/oauth2/v1/token",
            data={
                "grant_type": "client_credentials",
                "scope": self.scopes,
                "client_assertion_type": ASSERTION_TYPE,
                "client_assertion": self.client_assertion(),
            },
            headers={"Accept": "application/json", "User-Agent": "jml-agent/0.1.0"},
        )
        self._raise_for_status(response)
        body = response.json()
        self._access_token = str(body["access_token"])
        self._token_expiry = time.time() + int(body.get("expires_in", 3600)) - 30
        return self._access_token

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self._token()}",
            "Accept": "application/json",
            "User-Agent": "jml-agent/0.1.0",
        }
        extra = kwargs.pop("headers", {})
        headers.update(extra)
        return self.client.request(method, f"{self.org_url}{path}", headers=headers, **kwargs)

    def _group_id(self, name: str) -> str:
        cached = self._group_ids.get(name)
        if cached:
            return cached
        response = self._request("GET", "/api/v1/groups", params={"q": name, "limit": "20"})
        self._raise_for_status(response)
        for item in response.json():
            if item.get("profile", {}).get("name") == name:
                self._group_ids[name] = item["id"]
                return item["id"]
        raise OktaLiveError(f"Okta group {name} was not found.")

    def _require(self, email: str) -> dict[str, Any]:
        user = self.get_user(email)
        if user is None:
            raise OktaLiveError(f"Okta user {email} was not found.")
        return user

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise OktaLiveError(f"Okta returned HTTP {response.status_code}.")


def _user_view(payload: dict[str, Any]) -> dict[str, Any]:
    profile = payload.get("profile") or {}
    status = str(payload.get("status", "")).lower()
    mapped = {
        "active": "active",
        "provisioned": "active",
        "staged": "staged",
        "suspended": "suspended",
        "deprovisioned": "deprovisioned",
    }.get(status, status or "unknown")
    return {
        "id": payload.get("id", ""),
        "email": profile.get("email") or profile.get("login", ""),
        "first_name": profile.get("firstName", ""),
        "last_name": profile.get("lastName", ""),
        "department": profile.get("department", ""),
        "title": profile.get("title", ""),
        "manager_email": profile.get("manager") or "",
        "status": mapped,
        "mfa_enrolled": None,
    }
