"""Shared helper for CLI-JSON-family sources — dig a dotted path into nested dicts.

Used by both ``cli_json`` and ``tracker`` (any source that maps a tool's JSON into the model), so the
digging discipline lives in one place instead of a per-source copy.
"""

from __future__ import annotations

from typing import Any


def dig(obj: Any, path: str) -> Any:
    """Follow a dotted path into nested dicts; return None if any hop is absent."""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur
