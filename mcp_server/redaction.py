"""Allow-list tool output and strip values that should never reach a model."""

from __future__ import annotations

import re
from typing import Any

USER_FIELDS = (
    "id",
    "email",
    "first_name",
    "last_name",
    "display_name",
    "department",
    "title",
    "manager_email",
    "status",
    "mfa_enrolled",
)

DEVICE_FIELDS = (
    "id",
    "email",
    "platform",
    "os_version",
    "filevault",
    "edr_status",
    "last_checkin",
    "compliant",
    "source",
    "assignment_status",
)

_SECRET_KEYS = {
    "password",
    "secret",
    "token",
    "access_token",
    "private_key",
    "authorization",
    "ssn",
    "api_token",
    "client_assertion",
}

_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_LONG_DIGITS = re.compile(r"\b\d{13,19}\b")
_BEARER = re.compile(r"(?i)\bbearer\s+[a-z0-9._\-]+")
_ASSIGNMENT = re.compile(r"(?i)\b(password|token|secret|api[_-]?key)\s*=\s*\S+")


def redact_text(value: str) -> str:
    cleaned = _SSN.sub("[redacted]", value)
    cleaned = _LONG_DIGITS.sub("[redacted]", cleaned)
    cleaned = _BEARER.sub("[redacted]", cleaned)
    cleaned = _ASSIGNMENT.sub("[redacted]", cleaned)
    return cleaned


def allow(record: dict[str, Any] | None, fields: tuple[str, ...]) -> dict[str, Any] | None:
    if record is None:
        return None
    return {key: record.get(key) for key in fields}


def user_view(record: dict[str, Any] | None) -> dict[str, Any] | None:
    view = allow(record, USER_FIELDS)
    if view is None:
        return None
    first = view.get("first_name") or ""
    last = view.get("last_name") or ""
    view["display_name"] = f"{first} {last}".strip()
    enrolled = view.get("mfa_enrolled")
    view["mfa_enrolled"] = None if enrolled is None else bool(enrolled)
    return view


def device_view(record: dict[str, Any]) -> dict[str, Any]:
    view = allow(record, DEVICE_FIELDS) or {}
    view["filevault"] = bool(view.get("filevault"))
    view["compliant"] = bool(view.get("compliant"))
    view["source"] = record.get("source") or "MOCK:device-inventory"
    return view


def scrub(value: Any) -> Any:
    """Drop secret-looking keys and redact strings inside audit details."""
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in _SECRET_KEYS:
                cleaned[str(key)] = "[redacted]"
            else:
                cleaned[str(key)] = scrub(item)
        return cleaned
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact_text(str(value))
