"""Composition — the first genuine cross-source JOIN in iris (Brief C6).

``federate()`` fans out and concatenates; it does not join across sources. This module owns the
cross-source composition the seam rule assigns to iris: it groups the issue nodes (from a tracker
source) under the repo nodes (from constellation) by shared repo **identity** — the repo→issue
``Relation`` the tracker emits is the join carrier. An issue whose identity matches no repo node is
surfaced as ``unmatched`` (the Brief F6 identity-miss signal, made visible — never swallowed), not
dropped. Pure and read-only: it derives on read and persists nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from iris.core.federation import FederationResult
from iris.core.model import Node

_HAS_OPEN_ISSUE = "has-open-issue"


@dataclass(frozen=True)
class RepoWithIssues:
    """One composed unit — a repo node and its open issues."""

    repo: Node
    issues: list[Node] = field(default_factory=list)


@dataclass
class Composition:
    """The composed cross-source result: repos with their open issues, plus identity misses."""

    repos: list[RepoWithIssues] = field(default_factory=list)
    unmatched: list[Node] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def compose_repo_issues(result: FederationResult) -> Composition:
    """Join issue nodes under repo nodes by identity, preserving repo order.

    The relation ``(<identity>, "has-open-issue", <issue id>)`` is the join key; an issue whose
    identity matches no repo node lands in ``unmatched`` with a note.
    """
    issues_by_id = {n.id: n for n in result.nodes if n.kind == "issue"}
    repo_nodes = [n for n in result.nodes if n.kind == "repo"]
    repo_ids = {n.id for n in repo_nodes}

    # identity -> ordered issue node ids, from the join relations
    edges: dict[str, list[str]] = {}
    for rel in result.relations:
        if rel.type == _HAS_OPEN_ISSUE:
            edges.setdefault(rel.from_, []).append(rel.to)

    repos = [
        RepoWithIssues(
            repo=repo,
            issues=[issues_by_id[iid] for iid in edges.get(repo.id, []) if iid in issues_by_id],
        )
        for repo in repo_nodes
    ]

    unmatched = [
        issues_by_id[iid]
        for identity, iids in edges.items()
        if identity not in repo_ids
        for iid in iids
        if iid in issues_by_id
    ]

    notes: list[str] = []
    if unmatched:
        misses = sorted({identity for identity in edges if identity not in repo_ids})
        notes.append(
            f"unmatched: {len(unmatched)} open issue(s) for {len(misses)} identity(ies) with no repo "
            f"node ({', '.join(misses)}) — identity-miss (Brief F6)"
        )

    return Composition(repos=repos, unmatched=unmatched, notes=notes)
