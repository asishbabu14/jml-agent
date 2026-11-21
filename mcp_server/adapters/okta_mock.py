"""MOCK Okta directory. No network. State lives in the lab SQLite file."""

from __future__ import annotations

from typing import Any

from mcp_server.store import Store, new_id, utc_now


class OktaMockAdapter:
    backend_label = "MOCK"
    backend_name = "OktaMockAdapter"

    def __init__(self, store: Store) -> None:
        self.store = store

    def get_user(self, email: str) -> dict[str, Any] | None:
        return self.store.get_user(email)

    def list_groups(self, email: str) -> list[str]:
        return self.store.groups_for(email)

    def provision_user(self, profile: dict[str, Any]) -> dict[str, Any]:
        existing = self.store.get_user(profile["email"])
        row = {
            "email": profile["email"],
            "id": existing["id"] if existing else new_id("mock"),
            "first_name": profile.get("first_name", ""),
            "last_name": profile.get("last_name", ""),
            "department": profile.get("department", ""),
            "title": profile.get("title", ""),
            "manager_email": profile.get("manager_email", ""),
            "status": "active",
            "mfa_enrolled": False,
            "mfa_reset_at": None,
            "sessions_cleared_at": None,
        }
        self.store.upsert_user(row)
        return row

    def update_user(self, email: str, department: str, title: str) -> dict[str, Any]:
        user = self._require(email)
        user["department"] = department
        user["title"] = title
        self.store.upsert_user(user)
        return user

    def add_to_group(self, email: str, group: str) -> None:
        self._require(email)
        if not self.store.group_exists(group):
            raise KeyError(group)
        self.store.add_membership(email, group)

    def remove_groups(self, email: str, groups: list[str]) -> list[str]:
        self.store.remove_memberships(email, groups)
        return groups

    def remove_all_groups(self, email: str) -> list[str]:
        return self.store.remove_all_memberships(email)

    def deactivate(self, email: str) -> dict[str, Any]:
        user = self._require(email)
        user["status"] = "deprovisioned"
        self.store.upsert_user(user)
        return user

    def suspend(self, email: str) -> dict[str, Any]:
        user = self._require(email)
        user["status"] = "suspended"
        self.store.upsert_user(user)
        return user

    def clear_sessions(self, email: str) -> dict[str, Any]:
        user = self._require(email)
        user["sessions_cleared_at"] = utc_now()
        self.store.upsert_user(user)
        return {"email": email, "sessions_cleared": True}

    def reset_mfa(self, email: str) -> dict[str, Any]:
        user = self._require(email)
        user["mfa_enrolled"] = False
        user["mfa_reset_at"] = utc_now()
        self.store.upsert_user(user)
        return {"email": email, "mfa_enrolled": False}

    def _require(self, email: str) -> dict[str, Any]:
        user = self.store.get_user(email)
        if user is None:
            raise KeyError(email)
        return user
