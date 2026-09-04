"""``tracker`` source — open issues per repo from a forge CLI (gh/glab), keyed to repos by identity.

Source-agnostic by construction (Brief C7): the config declares WHICH forge CLI to run and how to map
its JSON — never an org, host, or instance. Issues are resolved by running the forge CLI with ``cwd``
set to each repo's local checkout, so the forge coordinates (owner/host/token) live only in the
checkout's own git remote, never in iris. Each open issue becomes a ``Node(kind="issue")`` plus a
``Relation(<repo-identity>, "has-open-issue", …)`` so the composer can group it under its repo. The
subprocess runner is injected so normalization is testable without gh/glab installed; a per-repo
failure (forge absent / unauthenticated / timeout / bad JSON) degrades that repo only — never a raise
that sinks the federation.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Callable

from iris.core.model import Node, Relation
from iris.core.registry import DEFAULT
from iris.core.source import KIND_NODES, Query, Source, SourceResult
from iris.sources._json import dig
from iris.sources._repos import identity, repo_paths

# A runner takes the forge argv and the repo checkout to run it in, and returns stdout.
Runner = Callable[[list[str], Path], str]

_DEFAULT_TIMEOUT = 30.0


def _make_default_runner(timeout: float) -> Runner:
    """A runner that enforces a timeout and runs in the repo checkout — a hung/failing forge CLI
    raises, which ``read`` isolates into a per-repo note rather than sinking the read."""

    def _run(cmd: list[str], cwd: Path) -> str:
        # Same caller-marker discipline as cli_json: a source CLI can detect it was invoked BY iris.
        env = {**os.environ, "IRIS_CALLER": "iris"}
        return subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True, timeout=timeout, env=env
        ).stdout

    return _run


class TrackerSource:
    """A read-only source over a forge issue-list CLI, one invocation per repo checkout."""

    # Emits the node graph (issue nodes + repo->issue relations); no hits. A hits-only query
    # (e.g. ``ground``) skips it — no forge subprocess spawned for a discarded read.
    produces = frozenset({KIND_NODES})

    def __init__(self, name: str, options: dict | None = None, runner: Runner | None = None) -> None:
        opts = options or {}
        self.name = name
        self._timeout = float(opts.get("timeout", _DEFAULT_TIMEOUT))
        self._runner = runner if runner is not None else _make_default_runner(self._timeout)
        self._mrconfig = opts.get("mrconfig", "~/.mrconfig")
        self._command: list[str] = list(opts.get("command", []))
        self._items_path: str = opts.get("items", "")
        self._map: dict[str, str] = dict(opts.get("map", {}))

    def read(self, query: Query) -> SourceResult:
        mrconfig = Path(os.path.realpath(os.path.expanduser(self._mrconfig)))
        try:
            repos = repo_paths(mrconfig)
        except OSError as exc:
            return SourceResult(ok=False, note=f"cannot read mrconfig ({exc})")
        nodes: list[Node] = []
        relations: list[Relation] = []
        failed = 0
        for repo in repos:
            ident = identity(repo)
            try:
                data = json.loads(self._runner(list(self._command), repo))
            except Exception:  # per-repo isolation: absent/unauth/timeout/bad-JSON degrades this repo
                failed += 1
                continue
            items = dig(data, self._items_path) if self._items_path else data
            if not isinstance(items, list):
                # unexpected shape (e.g. a wrapped object with `items` mis-configured): degrade this
                # repo rather than iterate a dict's keys into malformed `#None` nodes.
                failed += 1
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                number = dig(item, self._map.get("number", "number"))
                if number is None:
                    continue  # an issue without an identifiable number cannot key a stable node
                node_id = f"{ident}#{number}"
                nodes.append(
                    Node(
                        id=node_id,
                        kind="issue",
                        title=str(dig(item, self._map.get("title", "title")) or ""),
                        source=self.name,
                    )
                )
                relations.append(Relation(from_=ident, type="has-open-issue", to=node_id))
        note = ""
        ok = True
        if failed:
            note = f"{failed}/{len(repos)} repos unreadable (forge absent/unauth/timeout/unexpected-shape)"
            ok = False
        return SourceResult(nodes=nodes, relations=relations, ok=ok, note=note)


def _factory(name: str, options: dict) -> Source:
    return TrackerSource(name, options)


DEFAULT.register("tracker", _factory)
