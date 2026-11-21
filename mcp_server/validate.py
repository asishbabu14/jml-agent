"""Input checks. Tool arguments are untrusted."""

from __future__ import annotations

import re

from mcp_server.catalog import GROUP_NAMES, KNOWN_DEPARTMENTS, TICKET_CATEGORIES, TICKET_URGENCIES

EMAIL_RE = re.compile(r"^[a-z0-9._+-]+@[a-z0-9.-]+\.[a-z]{2,}$")
GROUP_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


class InputError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def email(value: str) -> str:
    cleaned = value.strip().lower()
    if not EMAIL_RE.fullmatch(cleaned) or len(cleaned) > 120:
        raise InputError("Email must look like name@lab.example.")
    return cleaned


def group_name(value: str) -> str:
    cleaned = value.strip().lower()
    if not GROUP_RE.fullmatch(cleaned) or cleaned not in GROUP_NAMES:
        raise InputError("Group is not in the lab catalog.")
    return cleaned


def department(value: str) -> str:
    cleaned = _short_text(value, 80)
    if cleaned not in KNOWN_DEPARTMENTS:
        raise InputError("Department is not in the lab catalog.")
    return cleaned


def title(value: str) -> str:
    return _short_text(value, 80)


def reason(value: str) -> str:
    return _short_text(value, 500)


def summary(value: str) -> str:
    return _short_text(value, 300)


def query(value: str) -> str:
    return _short_text(value, 300)


def category(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned not in TICKET_CATEGORIES:
        raise InputError("Category must be one of: " + ", ".join(sorted(TICKET_CATEGORIES)) + ".")
    return cleaned


def urgency(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned not in TICKET_URGENCIES:
        raise InputError("Urgency must be low, normal, or high.")
    return cleaned


def _short_text(value: str, limit: int) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > limit or CONTROL_CHARS.search(cleaned):
        raise InputError(f"Text must be 1-{limit} characters with no control characters.")
    return cleaned
