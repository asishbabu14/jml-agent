"""MOCK Google Workspace directory. No domain, no service account, no GAM process."""

from __future__ import annotations

from typing import Any

from mcp_server.store import Store


class GoogleWorkspaceMock:
    backend_label = "MOCK"
    backend_name = "GoogleWorkspaceMock"

    def __init__(self, store: Store) -> None:
        self.store = store
        self.memberships: dict[str, set[str]] = {}

    def get_user(self, email: str) -> dict[str, Any] | None:
        row = self.store.get_google(email)
        if row is None:
            return None
        row["groups"] = sorted(self.memberships.get(email, set()))
        row["backend"] = self.backend_label
        return row

    def ensure_user(self, profile: dict[str, Any]) -> dict[str, Any]:
        email = profile["email"]
        existing = self.store.get_google(email)
        if existing and existing["status"] == "suspended":
            self.store.set_google(email, status="active", drive_transferred_to=None, drive_status="in_place")
        elif existing is None:
            self.store.upsert_google(email, "active")
        self.memberships.setdefault(email, set())
        return self.get_user(email) or {}

    def update_user(self, email: str, department: str, title: str) -> dict[str, Any]:
        # The mock user table does not store department; the identity adapter does.
        # The call exists so the lifecycle still touches Workspace on a move.
        del department, title
        user = self.get_user(email)
        if user is None:
            raise KeyError(email)
        return user

    def suspend_user(self, email: str) -> dict[str, Any]:
        if self.get_user(email) is None:
            raise KeyError(email)
        self.store.set_google(email, status="suspended")
        return self.get_user(email) or {}

    def transfer_drive(self, email: str, to_email: str) -> dict[str, Any]:
        """Record a transfer. No files are copied and nothing leaves the process."""
        if self.get_user(email) is None:
            raise KeyError(email)
        self.store.set_google(email, drive_transferred_to=to_email, drive_status="transferred")
        return {
            "email": email,
            "drive_transferred_to": to_email,
            "drive_status": "transferred",
            "note": "MOCK transfer. No Drive bytes were moved.",
        }

    def add_to_group(self, email: str, group: str) -> None:
        self.memberships.setdefault(email, set()).add(group)

    def remove_all_groups(self, email: str) -> None:
        self.memberships[email] = set()
