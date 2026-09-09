"""``tasks`` source — open task-list items from a knowledge base, keyed to repos by identity.

The cross-source companion to ``tracker``: where the tracker brings a repo's open *issues*, this brings
the open *tasks* (a GTD/next-action list) that REFERENCE a repo — so ``context`` can join, under one
repo, both its open issues (from the forge) and the standing tasks about it (from the KB). The manual
composition this removes: reading the task list and the issue backlog separately and crossing them by
hand to see which tasks land on which repo (iris#29, the validated-need that earned this read).

Source-agnostic by construction (BR02): the config declares WHICH CLI lists the tasks and how to map
its JSON — never a store/instance. A task's repo linkage is not a field the KB carries; it is written
into the task TEXT as a ``<repo>#<number>`` reference (e.g. ``iris#29``). This source extracts those
references and emits a ``Relation(<repo-identity>, "has-task", <task id>)`` per referenced repo, leaving
the matched/unmatched decision to the composer (BR06) — exactly as the tracker emits ``has-open-issue``
and the composer resolves it against the repo nodes. A task with no reference contributes a node but no
relation (it is simply outside the cross-source join, never noise in it). The subprocess runner is
injected so normalization is testable without the CLI installed; a failed read degrades this source into
a note rather than a raise that sinks the federation (BR04).
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Callable

from iris.core.model import Node, Relation
from iris.core.registry import DEFAULT
from iris.core.source import KIND_CHAIN, KIND_NODES, Query, Source, SourceResult
from iris.sources._json import dig
from iris.sources._repos import parse_refs, repo_refs

Runner = Callable[[list[str]], str]

_DEFAULT_TIMEOUT = 30.0


def _make_default_runner(timeout: float) -> Runner:
    """A runner that enforces a timeout — a hung/failing CLI raises, which ``read`` isolates into a
    note rather than hanging or sinking the federation."""

    def _run(cmd: list[str]) -> str:
        # Same caller-marker discipline as the other subprocess sources: the child can detect it was
        # invoked BY iris.
        env = {**os.environ, "IRIS_CALLER": "iris"}
        return subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=timeout, env=env
        ).stdout

    return _run


class TasksSource:
    """A read-only source over a task-list CLI, one invocation for the whole open list."""

    # Emits the node graph (task nodes + repo->task relations) for ``context``, AND referenced-anchor
    # state for ``chain`` (KIND_CHAIN). No hits: a hits-only query (e.g. ``ground``) skips it.
    produces = frozenset({KIND_NODES, KIND_CHAIN})

    def __init__(self, name: str, options: dict | None = None, runner: Runner | None = None) -> None:
        opts = options or {}
        self.name = name
        self._timeout = float(opts.get("timeout", _DEFAULT_TIMEOUT))
        self._runner = runner if runner is not None else _make_default_runner(self._timeout)
        self._command: list[str] = list(opts.get("command", []))
        # The DONE-list command (F6-mínimo chain mode): the store lists open by default, so resolving a
        # referenced anchor that is already DONE needs its own read — e.g.
        # ["mneme", "task", "list", "--status", "done", "--json"]. Absent → a done anchor stays
        # unresolved (the composer marks it unknown), while open anchors still resolve from ``command``.
        self._done_command: list[str] = list(opts.get("done_command", []))
        self._items_path: str = opts.get("items", "")
        self._map: dict[str, str] = dict(opts.get("map", {}))

    def read(self, query: Query) -> SourceResult:
        # Kind-aware mode split (BR07): a ``chain`` query wants the state of the SPECIFIC anchors an
        # item references (incl. done); ``context``/bare reads keep the whole-open-queue path.
        if query.kinds is not None and KIND_CHAIN in query.kinds:
            return self._read_referenced(query)
        return self._read_open(query)

    def _read_open(self, query: Query) -> SourceResult:
        try:
            data = json.loads(self._runner(list(self._command)))
        except Exception as exc:  # absent/unauth/timeout/bad-JSON degrades this source, never a raise
            return SourceResult(ok=False, note=f"unreadable ({exc})")
        items = dig(data, self._items_path) if self._items_path else data
        if not isinstance(items, list):
            return SourceResult(ok=False, note="unexpected-shape (task list is not an array)")

        nodes: list[Node] = []
        relations: list[Relation] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            task_id = dig(item, self._map.get("id", "id"))
            if task_id is None:
                continue  # a task without an identifiable id cannot key a stable node
            node_id = str(task_id)
            text = str(dig(item, self._map.get("title", "text")) or "")
            nodes.append(Node(id=node_id, kind="task", title=text, source=self.name))
            # One relation per DISTINCT repo referenced — a task naming iris#29 and iris#31 lands under
            # iris once, not twice; a task naming two repos lands under both (repo_refs dedups).
            for slug in repo_refs(text):
                relations.append(Relation(from_=slug, type="has-task", to=node_id))
        return SourceResult(nodes=nodes, relations=relations, ok=True)

    def _read_referenced(self, query: Query) -> SourceResult:
        """Chain mode (F6-mínimo): resolve each SPECIFIC ``^anchor`` the query names to its GTD item,
        carrying lifecycle state (``roles=["open"]`` | ``["done"]``). An anchor found in neither list is
        simply not emitted — the chain composer surfaces it as unresolved/unknown, never as clear.
        """
        wanted = {r.anchor for r in parse_refs(query.text) if r.kind == "anchor"}
        if not wanted:
            return SourceResult(ok=True)
        nodes: list[Node] = []
        failed = 0
        for command, state in ((self._command, "open"), (self._done_command, "done")):
            if not command:
                continue
            try:
                data = json.loads(self._runner(list(command)))
            except Exception:  # per-list isolation (BR04): a failing list degrades, never raises
                failed += 1
                continue
            items = dig(data, self._items_path) if self._items_path else data
            if not isinstance(items, list):
                failed += 1
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                task_id = dig(item, self._map.get("id", "id"))
                if task_id is None or str(task_id) not in wanted:
                    continue
                text = str(dig(item, self._map.get("title", "text")) or "")
                # The task text carries any gate/trigger marker; the composer parses it. State is the
                # list this item came from.
                nodes.append(Node(id=str(task_id), kind="task", title=text, roles=[state], source=self.name))
        note = f"chain: {failed} list(s) unreadable" if failed else ""
        return SourceResult(nodes=nodes, ok=not failed, note=note)


def _factory(name: str, options: dict) -> Source:
    return TasksSource(name, options)


DEFAULT.register("tasks", _factory)
