"""Load the synthetic HR file, groups, and device inventory into a fresh store."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from mcp_server.catalog import GROUPS, groups_for
from mcp_server.store import Store, new_id


def load_employees(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def lifecycle_events(employees: list[dict[str, str]]) -> list[dict[str, str]]:
    """Events the HR file is asking the lab to process. Active rows are already seeded."""
    events: list[dict[str, str]] = []
    for person in employees:
        status = person.get("status", "")
        if status == "hired":
            events.append({**person, "event": "joiner"})
        elif status == "mover":
            events.append({**person, "event": "mover"})
        elif status == "leaving":
            events.append({**person, "event": "leaver"})
    return events


def seed(store: Store, hr_csv: Path, devices_path: Path) -> None:
    for person in load_employees(hr_csv):
        person["email"] = person["email"].lower()
        if person.get("manager_email"):
            person["manager_email"] = person["manager_email"].lower()
        store.upsert_hr(person)
    if store.get_meta("seeded") == "1":
        return
    for group in GROUPS:
        store.upsert_group(group.name, group.description, group.owner_email)
    for person in load_employees(hr_csv):
        email = person["email"].strip().lower()
        if person["status"] == "hired":
            continue
        store.upsert_user(
            {
                "email": email,
                "id": new_id("mock"),
                "first_name": person["first_name"],
                "last_name": person["last_name"],
                "department": person["department"],
                "title": person["title"],
                "manager_email": person["manager_email"].lower(),
                "status": "active",
                "mfa_enrolled": True,
            }
        )
        store.upsert_google(email, "active")
        for name in groups_for(person["department"], person["title"]):
            store.add_membership(email, name)
    devices = json.loads(devices_path.read_text(encoding="utf-8"))
    for device in devices:
        device["source"] = "MOCK:device-inventory"
        store.upsert_device(device)
    store.set_meta("seeded", "1")
