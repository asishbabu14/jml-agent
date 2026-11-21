"""Tool registration data. Handlers close over the service and the process actor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    scopes: tuple[str, ...]
    build: Callable[[Any, str], Callable[..., Any]]
    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False
