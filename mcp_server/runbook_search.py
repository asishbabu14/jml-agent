"""Keyword search over the runbook files. The query is data, not a command."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_TOKEN = re.compile(r"[a-z0-9]+")


def search(directory: Path, query: str, limit: int = 3) -> list[dict[str, Any]]:
    tokens = [token for token in _TOKEN.findall(query.lower()) if len(token) > 2]
    if not directory.is_dir() or not tokens:
        return []
    hits: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.md")):
        meta, body = _split(path.read_text(encoding="utf-8"))
        title = str(meta.get("title") or path.stem)
        tags = [str(tag).lower() for tag in (meta.get("tags") or [])]
        score = 0
        title_l = title.lower()
        body_l = body.lower()
        for token in tokens:
            if token in title_l:
                score += 3
            if any(token in tag for tag in tags):
                score += 2
            if token in body_l:
                score += 1
        if score <= 0:
            continue
        hits.append(
            {
                "title": title,
                "slug": path.stem,
                "audience": str(meta.get("audience") or ""),
                "tags": tags,
                "summary": str(meta.get("summary") or ""),
                "excerpt": body.strip()[:800],
                "score": score,
            }
        )
    hits.sort(key=lambda item: (-int(item["score"]), str(item["title"])))
    return hits[:limit]


def _split(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    loaded = yaml.safe_load(parts[1]) or {}
    if not isinstance(loaded, dict):
        return {}, parts[2]
    return loaded, parts[2]
