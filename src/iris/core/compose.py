"""Composition — the cross-source JOINs iris owns (Brief C6 / domain BR01).

``federate()`` fans out and concatenates; it does not join across sources. This module owns the
cross-source composition the seam rule assigns to iris: it groups the satellite nodes of a repo — its
open **issues** (from a tracker source) and the standing **tasks** that reference it (from a tasks
source) — under the repo nodes (from constellation) by shared repo **identity**. The relation each
source emits (``has-open-issue`` / ``has-task``) is the join carrier. A satellite whose identity matches
no repo node is surfaced as ``unmatched`` (the Brief F6 identity-miss signal, made visible — never
dropped), not swallowed. Pure and read-only: it derives on read and persists nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from iris.core.federation import FederationResult
from iris.core.model import Node
from iris.sources._repos import parse_refs

_HAS_OPEN_ISSUE = "has-open-issue"
_HAS_TASK = "has-task"

# A gate / blocked-by marker written into an item's prose — the data signal that a referenced node is
# holding the item, beyond the node's own open/closed state. Case-insensitive; conservative (only
# well-known markers) so ordinary prose is not swept in as a false blocker.
_GATE_MARKER = re.compile(r"gate:|trigger-source:|blocked[ -]by|-gate\b|gate\]", re.IGNORECASE)


@dataclass(frozen=True)
class ComposedRepo:
    """One composed unit — a repo node with its cross-source satellites (open issues + tasks)."""

    repo: Node
    issues: list[Node] = field(default_factory=list)
    tasks: list[Node] = field(default_factory=list)


@dataclass
class Composition:
    """The composed cross-source result: repos with their satellites, plus per-kind identity misses."""

    repos: list[ComposedRepo] = field(default_factory=list)
    unmatched: list[Node] = field(default_factory=list)  # issues matching no repo node
    unmatched_tasks: list[Node] = field(default_factory=list)  # tasks referencing no known repo
    notes: list[str] = field(default_factory=list)


def _grouped(
    result: FederationResult, kind: str, rel_type: str, repo_ids: set[str]
) -> tuple[dict[str, list[Node]], list[Node]]:
    """Resolve one satellite kind against the repo nodes by identity.

    Returns ``(by_repo, unmatched)``: nodes of ``kind`` grouped under their repo identity via the
    ``rel_type`` relations (repo order handled by the caller), and the nodes whose identity matches no
    repo. Relation order is preserved; an id seen twice under the same repo is kept once.
    """
    nodes_by_id = {n.id: n for n in result.nodes if n.kind == kind}
    edges: dict[str, list[str]] = {}
    for rel in result.relations:
        if rel.type == rel_type:
            seen = edges.setdefault(rel.from_, [])
            if rel.to not in seen:
                seen.append(rel.to)

    by_repo = {
        identity: [nodes_by_id[nid] for nid in nids if nid in nodes_by_id]
        for identity, nids in edges.items()
        if identity in repo_ids
    }
    # Dedup unmatched nodes across identities (a task naming two unknown repos surfaces once).
    unmatched_ids = [
        nid
        for identity, nids in edges.items()
        if identity not in repo_ids
        for nid in nids
        if nid in nodes_by_id
    ]
    unmatched = [nodes_by_id[nid] for nid in dict.fromkeys(unmatched_ids)]
    return by_repo, unmatched


def compose_repo_issues(result: FederationResult) -> Composition:
    """Join issue and task nodes under repo nodes by identity, preserving repo order.

    ``(<identity>, "has-open-issue"|"has-task", <node id>)`` is the join key; a satellite whose identity
    matches no repo node lands in the matching ``unmatched`` bucket with a note.
    """
    repo_nodes = [n for n in result.nodes if n.kind == "repo"]
    repo_ids = {n.id for n in repo_nodes}

    issues_by_repo, unmatched = _grouped(result, "issue", _HAS_OPEN_ISSUE, repo_ids)
    tasks_by_repo, unmatched_tasks = _grouped(result, "task", _HAS_TASK, repo_ids)

    repos = [
        ComposedRepo(
            repo=repo,
            issues=issues_by_repo.get(repo.id, []),
            tasks=tasks_by_repo.get(repo.id, []),
        )
        for repo in repo_nodes
    ]

    notes: list[str] = []
    if unmatched:
        misses = _miss_identities(result, _HAS_OPEN_ISSUE, repo_ids)
        notes.append(
            f"unmatched: {len(unmatched)} open issue(s) for {len(misses)} identity(ies) with no repo "
            f"node ({', '.join(misses)}) — identity-miss (Brief F6)"
        )
    if unmatched_tasks:
        misses = _miss_identities(result, _HAS_TASK, repo_ids)
        notes.append(
            f"unmatched: {len(unmatched_tasks)} task(s) reference {len(misses)} repo(s) outside the "
            f"constellation ({', '.join(misses)})"
        )

    return Composition(
        repos=repos, unmatched=unmatched, unmatched_tasks=unmatched_tasks, notes=notes
    )


def _miss_identities(result: FederationResult, rel_type: str, repo_ids: set[str]) -> list[str]:
    """The sorted distinct identities of ``rel_type`` edges that match no repo node."""
    return sorted({r.from_ for r in result.relations if r.type == rel_type and r.from_ not in repo_ids})


# --- F6-mínimo (iris#43): item ⋈ referenced-nodes ------------------------------------------------


@dataclass(frozen=True)
class ReferencedChain:
    """The ``item ⋈ referenced-nodes`` composition (F6-mínimo): the live state of the SPECIFIC nodes a
    work item references, plus which of them are data-derived candidate blockers.

    ``unresolved`` holds the ref strings iris could NOT resolve (fetch failed, or the ref names nothing
    known) — surfaced as UNKNOWN, never as clear: a non-empty ``unresolved`` means "nothing blocks"
    cannot be asserted, even with ``blocker_candidates`` empty. ``notes`` carries the federation's
    per-source degradation notes so the caller can tell a real miss from a source that was down.
    """

    item: str
    resolved: list[Node] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    blocker_candidates: list[Node] = field(default_factory=list)
    # Resolved nodes whose STATE could not be determined (empty roles — e.g. the `view` command's JSON
    # omitted the state field). Surfaced as UNKNOWN, never as "not blocking": a resolved node with no
    # known state is a SECOND unknown beside `unresolved`, so "nothing blocks" cannot be asserted while
    # this is non-empty either (the failure-mode guard, completed).
    state_unknown: list[Node] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _is_open(node: Node) -> bool:
    """A node is a live blocker only while OPEN — a closed issue / done task is discharged, never a
    candidate. State is carried in ``roles`` by the chain-mode source reads (F6-T2/T3)."""
    return "open" in {r.lower() for r in node.roles}


def is_gate_marked(node: Node) -> bool:
    """Whether the node's prose carries an explicit gate / blocked-by marker (a data signal for
    presentation emphasis — the operative blocker signal is open-state, this only enriches it)."""
    return bool(_GATE_MARKER.search(node.title))


def compose_referenced_nodes(item_text: str, result: FederationResult) -> ReferencedChain:
    """Join each ref parsed from ``item_text`` to the live node the sources resolved for it.

    An issue ref ``<slug>#<n>`` matches node id ``<slug>#<n>``; an anchor ref ``^<id>`` matches node id
    ``<id>``. A ref with no matching node is UNRESOLVED (unknown). A resolved node that is OPEN is a
    candidate blocker (a discharged closed/done node is not) — the data-derived signal; the final
    judgement is the consumer's (BR01/BR03: iris composes and marks, it does not decide).
    """
    by_id = {n.id: n for n in result.nodes}
    resolved: list[Node] = []
    unresolved: list[str] = []
    blocker_candidates: list[Node] = []
    state_unknown: list[Node] = []
    for ref in parse_refs(item_text):
        node_id = f"{ref.slug}#{ref.number}" if ref.kind == "issue" else str(ref.anchor)
        display = node_id if ref.kind == "issue" else f"^{node_id}"
        node = by_id.get(node_id)
        if node is None:
            if display not in unresolved:
                unresolved.append(display)
            continue
        if node not in resolved:
            resolved.append(node)
            if not node.roles:
                # Resolved, but state undetermined — UNKNOWN, never silently "not blocking".
                state_unknown.append(node)
            elif _is_open(node):
                blocker_candidates.append(node)
    return ReferencedChain(
        item=item_text,
        resolved=resolved,
        unresolved=unresolved,
        blocker_candidates=blocker_candidates,
        state_unknown=state_unknown,
        notes=list(result.notes),
    )
