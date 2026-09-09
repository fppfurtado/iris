"""``tracker`` source — open issues per repo from a forge CLI (gh/glab), keyed to repos by identity.

Source-agnostic by construction (Brief C7): the config declares WHICH forge CLI to run and how to map
its JSON — never an org, host, or instance. Issues are resolved by running the forge CLI with ``cwd``
set to each repo's local checkout, so the forge coordinates (owner/host/token) live only in the
checkout's own git remote, never in iris.

Scoped by the query, not the registry (iris#36): the fan-out is restricted to the repos the query
NAMES as ``<repo>#<n>`` — so ``context "mexer em iris#29"`` spawns the forge CLI only in ``iris``, and a
query naming no repo (a bare ``context``, or the ``repos``/``ground`` reads that carry no task text)
spawns nothing at all. This keeps the source ergonomic to enable in an active config over a large
registry, where the old all-repos sweep made every read pay one subprocess per checkout.

Each open issue becomes a ``Node(kind="issue")`` plus a
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
from iris.core.source import KIND_CHAIN, KIND_NODES, Query, Source, SourceResult
from iris.sources._json import dig
from iris.sources._repos import identity, parse_refs, repo_paths, repo_refs

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

    # Emits the node graph (issue nodes + repo->issue relations) for ``context``, AND referenced-issue
    # state for ``chain`` (KIND_CHAIN). No hits: a hits-only query (e.g. ``ground``) skips it — no forge
    # subprocess spawned for a discarded read.
    produces = frozenset({KIND_NODES, KIND_CHAIN})

    def __init__(self, name: str, options: dict | None = None, runner: Runner | None = None) -> None:
        opts = options or {}
        self.name = name
        self._timeout = float(opts.get("timeout", _DEFAULT_TIMEOUT))
        self._runner = runner if runner is not None else _make_default_runner(self._timeout)
        self._mrconfig = opts.get("mrconfig", "~/.mrconfig")
        self._command: list[str] = list(opts.get("command", []))
        # The per-issue VIEW command (F6-mínimo chain mode): fetches ONE issue by number incl. its
        # state (open/closed), source-agnostic via `{number}` substitution — e.g.
        # ["gh", "issue", "view", "{number}", "--json", "number,title,state"]. Absent → chain mode
        # degrades to a note (BR04), leaving ``context`` (the list command) untouched.
        self._view: list[str] = list(opts.get("view", []))
        self._items_path: str = opts.get("items", "")
        self._map: dict[str, str] = dict(opts.get("map", {}))

    def read(self, query: Query) -> SourceResult:
        # Kind-aware mode split (BR07): a ``chain`` query wants the LIVE state of the SPECIFIC issues an
        # item references (incl. CLOSED) — a different read than ``context``'s list of a repo's OPEN
        # issues. Route by the consumed kind; ``context``/bare reads keep the existing list path.
        if query.kinds is not None and KIND_CHAIN in query.kinds:
            return self._read_referenced(query)
        return self._read_open(query)

    def _read_open(self, query: Query) -> SourceResult:
        # Scoped by construction (iris#36): the tracker spawns a forge CLI only for the repos the query
        # NAMES as `<repo>#<n>`, not the whole registry. A query naming none — a bare `context`, or the
        # `repos`/`ground` reads that carry no task text — derives zero targets and returns empty with
        # no fan-out, no forge subprocess. (Config-time overrides like an explicit allowlist grow by
        # validated need — iris#36 chose query-derived + empty-fallback; no allowlist until one is felt.)
        wanted = set(repo_refs(query.text))
        if not wanted:
            return SourceResult(ok=True)
        mrconfig = Path(os.path.realpath(os.path.expanduser(self._mrconfig)))
        try:
            repos = repo_paths(mrconfig)
        except OSError as exc:
            return SourceResult(ok=False, note=f"cannot read mrconfig ({exc})")
        repos = [r for r in repos if identity(r) in wanted]
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

    def _read_referenced(self, query: Query) -> SourceResult:
        """Chain mode (F6-mínimo): fetch the LIVE state of each SPECIFIC ``<repo>#<n>`` the query names.

        Unlike ``_read_open`` this resolves refs to individual issues via the per-issue ``view`` command
        (state incl. CLOSED, carried in ``roles``). A ref whose fetch fails degrades that ref into a
        note (BR04) — the chain composer surfaces it as unresolved/unknown, never as clear.
        """
        refs = [r for r in parse_refs(query.text) if r.kind == "issue"]
        if not refs:
            return SourceResult(ok=True)
        if not self._view:
            return SourceResult(ok=False, note="chain: no `view` command configured (BR04)")
        mrconfig = Path(os.path.realpath(os.path.expanduser(self._mrconfig)))
        try:
            paths = {identity(p): p for p in repo_paths(mrconfig)}
        except OSError as exc:
            return SourceResult(ok=False, note=f"cannot read mrconfig ({exc})")
        nodes: list[Node] = []
        failed = 0
        for ref in refs:
            repo = paths.get(ref.slug)
            if repo is None:
                continue  # a ref to a repo outside the registry — the composer marks it unresolved
            cmd = [arg.replace("{number}", str(ref.number)) for arg in self._view]
            try:
                data = json.loads(self._runner(cmd, repo))
            except Exception:  # per-ref isolation: absent/unauth/timeout/bad-JSON degrades this ref
                failed += 1
                continue
            if not isinstance(data, dict):
                failed += 1
                continue
            state = str(dig(data, self._map.get("state", "state")) or "").lower()
            nodes.append(
                Node(
                    id=f"{ref.slug}#{ref.number}",
                    kind="issue",
                    title=str(dig(data, self._map.get("title", "title")) or ""),
                    roles=[state] if state else [],
                    source=self.name,
                )
            )
        note = f"chain: {failed} ref(s) unreadable (forge absent/unauth/timeout)" if failed else ""
        return SourceResult(nodes=nodes, ok=not failed, note=note)


def _factory(name: str, options: dict) -> Source:
    return TrackerSource(name, options)


DEFAULT.register("tracker", _factory)
