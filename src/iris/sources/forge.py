"""``forge-repos`` source — the repo listing of each configured forge org, for a universe-kind read.

Source-agnostic by construction (BR02): the config declares the forge ``host`` (part of every slug), the
``orgs`` to list, the listing ``command`` (an argv template with an ``{org}`` placeholder — a ``gh`` or
``glab`` call) and a ``map`` of ``path`` / ``archived`` to the dotted JSON fields of each listed repo. No
org, host or instance lives in code. Several forges are several instances of this type.

The command runs once per org. Each listed repo becomes a ``repo`` node with ``origin="forge"``,
``attrs.slug = "<host>/<full path>"`` (normalised like a local slug, every path segment kept) and
``attrs.archived``. One ``scope`` node per org records whether that org was read, so a composer can bound
its forge comparisons to the host+orgs actually read. A failing org (command error, timeout, bad JSON)
degrades that org only: the others still count and the note says the listing is ``incomplete`` (BR04 at
org granularity). The source produces only the universe kind, so ``repos``/``context``/``chain`` never
call the forge. The subprocess runner is injected so it is testable without a forge CLI installed.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Callable

from iris.core.model import Node
from iris.core.registry import DEFAULT
from iris.core.source import KIND_UNIVERSE, Query, Source, SourceResult
from iris.sources._json import dig
from iris.sources._repos import forge_slug

Runner = Callable[[list[str]], str]

_DEFAULT_TIMEOUT = 60.0


def _make_default_runner(timeout: float) -> Runner:
    """A runner that enforces a timeout — a hung forge CLI raises, which ``read`` isolates per org."""

    def _run(cmd: list[str]) -> str:
        # Same caller-marker discipline as the other CLI sources.
        env = {**os.environ, "IRIS_CALLER": "iris"}
        return subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=timeout, env=env
        ).stdout

    return _run


class ForgeReposSource:
    """A read-only source over a forge repo-listing CLI, one invocation per configured org."""

    produces = frozenset({KIND_UNIVERSE})

    def __init__(self, name: str, options: dict | None = None, runner: Runner | None = None) -> None:
        opts = options or {}
        self.name = name
        self._timeout = float(opts.get("timeout", _DEFAULT_TIMEOUT))
        self._runner = runner if runner is not None else _make_default_runner(self._timeout)
        self._host: str = str(opts.get("host", "")).strip()
        self._orgs: list[str] = [str(o) for o in opts.get("orgs", [])]
        self._command: list[str] = list(opts.get("command", []))
        self._items_path: str = opts.get("items", "")
        self._map: dict[str, str] = dict(opts.get("map", {}))

    def read(self, query: Query) -> SourceResult:
        if not self._host:
            scope = self._scope(self.name, org="", read=False)
            return SourceResult(nodes=[scope], ok=False, note="no `host` configured; no slug can be formed")
        nodes: list[Node] = []
        failed: list[str] = []
        for org in self._orgs:
            try:
                repos = self._list(org)
            except Exception as exc:  # per-org isolation (BR04)
                failed.append(f"{org} ({exc})")
                nodes.append(self._scope(f"{self._host}/{org}", org=org, read=False))
                continue
            nodes.append(self._scope(f"{self._host}/{org}", org=org, read=True))
            nodes.extend(repos)
        if failed and len(failed) == len(self._orgs):
            return SourceResult(nodes=nodes, ok=False, note=f"every org failed: {'; '.join(failed)}")
        note = f"incomplete: org {'; '.join(failed)} failed" if failed else ""
        return SourceResult(nodes=nodes, ok=True, note=note)

    def _list(self, org: str) -> list[Node]:
        argv = [part.replace("{org}", org) for part in self._command]
        data = json.loads(self._runner(argv))
        items = dig(data, self._items_path) if self._items_path else data
        if not isinstance(items, list):
            raise ValueError("listing is not a JSON list")
        nodes: list[Node] = []
        for item in items:
            path = dig(item, self._map.get("path", "path"))
            slug = forge_slug(f"https://{self._host}/{path}") if path else None
            if not slug:
                continue
            nodes.append(
                Node(
                    id=slug.rsplit("/", 1)[-1],
                    kind="repo",
                    title=slug,
                    source=self.name,
                    attrs={
                        "origin": "forge",
                        "slug": slug,
                        "archived": bool(dig(item, self._map.get("archived", "archived"))),
                    },
                )
            )
        return nodes

    def _scope(self, key: str, org: str, read: bool) -> Node:
        return Node(
            id=f"forge:{key}",
            kind="scope",
            title=key,
            source=self.name,
            attrs={"dimension": "forge", "host": self._host.lower(), "org": org.lower(), "read": read},
        )


def _factory(name: str, options: dict) -> Source:
    return ForgeReposSource(name, options)


DEFAULT.register("forge-repos", _factory)
