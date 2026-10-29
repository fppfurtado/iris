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
import os
import subprocess
from typing import Callable

from iris.core.model import GroundHit, Node
from iris.core.registry import DEFAULT
from iris.core.source import KIND_HITS, KIND_INBOUND, Query, Source, SourceResult
from iris.sources._json import dig

Runner = Callable[[list[str]], str]

_DEFAULT_TIMEOUT = 30.0


def _make_default_runner(timeout: float) -> Runner:
    """A runner that enforces a timeout — a hung CLI raises TimeoutExpired, which
    federation isolates into a note rather than hanging the whole read."""

    def _run(cmd: list[str]) -> str:
        # Inject a generic caller marker into the child environment so any source CLI
        # iris shells out to can detect it was invoked BY iris (vs. called directly by
        # something else). Generic by construction — no tool is special-cased.
        env = {**os.environ, "IRIS_CALLER": "iris"}
        return subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=timeout, env=env
        ).stdout

    return _run


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
        # The inbound read (item inbound context): a second, optional command answering "which records
        # cite <key>". Only an instance that configures it declares ``inbound`` — an un-configured one is
        # never read for an inbound query.
        self._inbound: dict = dict(opts.get("inbound", {}))
        if self._inbound:
            self.produces = frozenset({KIND_HITS, KIND_INBOUND})

    def read(self, query: Query) -> SourceResult:
        if self._inbound and query.kinds is not None and KIND_INBOUND in query.kinds:
            return self._read_citations(query)
        argv = [part.replace("{query}", query.text) for part in self._command]
        data = json.loads(self._runner(argv))
        items = dig(data, self._items_path) or []
        hits = [self._hit(item) for item in items]
        return SourceResult(hits=hits)

    def _read_citations(self, query: Query) -> SourceResult:
        """One ``Node(kind="citation")`` per record the inbound command returns for ``{key}``.

        The key is passed through as one argv element; the store resolves which records cite it (its own
        within-source identity) — a citation record carries no text to re-match. Records whose locator
        starts with a ``skip`` prefix are dropped. A failed read or a non-array degrades, never raises.
        """
        argv = [part.replace("{key}", query.text.strip()) for part in self._inbound.get("command", [])]
        items_path: str = self._inbound.get("items", "")
        fields: dict[str, str] = dict(self._inbound.get("map", {}))
        skip: list[str] = list(self._inbound.get("skip", []))
        try:
            data = json.loads(self._runner(argv))
        except Exception as exc:
            return SourceResult(ok=False, note=f"inbound: unreadable ({exc})")
        items = dig(data, items_path) if items_path else data
        if not isinstance(items, list):
            return SourceResult(ok=False, note="inbound: unexpected-shape (not an array)")
        nodes: list[Node] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            locator = str(dig(item, fields.get("locator", "source")) or "")
            if not locator or any(locator.startswith(prefix) for prefix in skip):
                continue
            link_type = str(dig(item, fields.get("type", "type")) or "")
            roles = [link_type] if link_type else []
            nodes.append(Node(id=locator, kind="citation", title=locator, roles=roles, source=self.name))
        return SourceResult(nodes=nodes)

    def _hit(self, item: dict) -> GroundHit:
        age_path = self._map.get("age")
        age_val = dig(item, age_path) if age_path else None
        trust_path = self._map.get("trust")
        return GroundHit(
            ref=str(dig(item, self._map.get("ref", "ref")) or ""),
            excerpt=str(dig(item, self._map.get("excerpt", "excerpt")) or ""),
            trust=str(dig(item, trust_path) or "") if trust_path else "",
            age=f"{age_val}d" if age_val is not None else "",
        )


def _factory(name: str, options: dict) -> Source:
    return CliJsonSource(name, options)


DEFAULT.register("cli-json", _factory)
