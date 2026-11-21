"""Local ticket store. Ravenna-shaped fields, not a Ravenna connection."""

from __future__ import annotations

from typing import Any

from mcp_server.catalog import TICKET_OWNERS
from mcp_server.store import Store, new_id, utc_now


class TicketStore:
    backend_label = "MOCK"
    backend_name = "LocalTicketStore"

    def __init__(self, store: Store) -> None:
        self.store = store

    def create(self, summary: str, category: str, urgency: str, requester: str) -> dict[str, Any]:
        row = {
            "id": new_id("tkt"),
            "summary": summary,
            "category": category,
            "urgency": urgency,
            "status": "open",
            "owner": TICKET_OWNERS[category],
            "requester": requester,
            "created_at": utc_now(),
        }
        return self.store.create_ticket(row)
