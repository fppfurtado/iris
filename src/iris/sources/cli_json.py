"""Generic ``cli-json`` source — shell out to any ``--json`` CLI and normalize.

Config-driven so it names no specific tool: an instance declares a ``command`` (an
argv template with a ``{query}`` placeholder), the ``items`` path to the result list,
and a ``map`` of model field → dotted JSON path. Any sovereign CLI that emits JSON
(a knowledge base, a notes tool, …) becomes a source through configuration alone —
no code in the core references it. The subprocess is injected as a ``runner`` so
normalization is testable without the tool installed.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Callable

from iris.core.model import GroundHit
from iris.core.registry import DEFAULT
from iris.core.source import KIND_HITS, Query, Source, SourceResult

Runner = Callable[[list[str]], str]

_DEFAULT_TIMEOUT = 30.0


def _make_default_runner(timeout: float) -> Runner:
    """A runner that enforces a timeout — a hung CLI raises TimeoutExpired, which
    federation isolates into a note rather than hanging the whole read."""

    def _run(cmd: list[str]) -> str:
        return subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=timeout).stdout

    return _run


def _dig(obj: Any, path: str) -> Any:
    """Follow a dotted path into nested dicts; return None if any hop is absent."""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


class CliJsonSource:
    """A read-only source over a configured ``--json`` CLI command."""

    # Emits grounding hits only; contributes no nodes/relations. A node-only query
    # (e.g. ``repos``) skips this source — no subprocess is spawned for a discarded read.
    produces = frozenset({KIND_HITS})

    def __init__(self, name: str, options: dict | None = None, runner: Runner | None = None) -> None:
        opts = options or {}
        self.name = name
        self._timeout = float(opts.get("timeout", _DEFAULT_TIMEOUT))
        self._runner = runner if runner is not None else _make_default_runner(self._timeout)
        self._command: list[str] = list(opts.get("command", []))
        self._items_path: str = opts.get("items", "items")
        self._map: dict[str, str] = dict(opts.get("map", {}))

    def read(self, query: Query) -> SourceResult:
        argv = [part.replace("{query}", query.text) for part in self._command]
        data = json.loads(self._runner(argv))
        items = _dig(data, self._items_path) or []
        hits = [self._hit(item) for item in items]
        return SourceResult(hits=hits)

    def _hit(self, item: dict) -> GroundHit:
        age_path = self._map.get("age")
        age_val = _dig(item, age_path) if age_path else None
        trust_path = self._map.get("trust")
        return GroundHit(
            ref=str(_dig(item, self._map.get("ref", "ref")) or ""),
            excerpt=str(_dig(item, self._map.get("excerpt", "excerpt")) or ""),
            trust=str(_dig(item, trust_path) or "") if trust_path else "",
            age=f"{age_val}d" if age_val is not None else "",
        )


def _factory(name: str, options: dict) -> Source:
    return CliJsonSource(name, options)


DEFAULT.register("cli-json", _factory)
