"""MOCK device inventory in the shape of an Iru-style posture record.

This is not a connection to Iru, SentinelOne, or any MDM tenant.
"""

from __future__ import annotations

from typing import Any

from mcp_server.store import Store, new_id


class DeviceMock:
    backend_label = "MOCK"
    backend_name = "IruStyleDeviceMock"
    source = "MOCK:iru-style"

    def __init__(self, store: Store) -> None:
        self.store = store

    def for_user(self, email: str) -> list[dict[str, Any]]:
        devices = self.store.devices_for(email)
        for device in devices:
            device["source"] = device.get("source") or self.source
        return devices

    def ensure_pending(self, email: str) -> dict[str, Any]:
        current = self.for_user(email)
        if current:
            return current[0]
        row = {
            "id": new_id("dev"),
            "email": email,
            "platform": "unassigned",
            "os_version": "",
            "filevault": False,
            "edr_status": "unknown",
            "last_checkin": "",
            "compliant": False,
            "source": self.source,
            "assignment_status": "pending_enrollment",
        }
        self.store.upsert_device(row)
        return row

    def release(self, email: str) -> list[str]:
        return self.store.release_devices(email)
