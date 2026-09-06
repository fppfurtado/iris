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

from dataclasses import dataclass, field

from iris.core.federation import FederationResult
from iris.core.model import Node

_HAS_OPEN_ISSUE = "has-open-issue"
_HAS_TASK = "has-task"


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
