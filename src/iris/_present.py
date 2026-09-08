"""Presentation-layer scoping for the ``context`` read — shared by the CLI and the MCP adapter.

The composer (``compose_repo_issues``) keeps the FULL repo roster; deciding which composed repos are
worth *showing* for a given query is a presentation concern, kept here so both surfaces scope
identically (no drift between the CLI text and the MCP dict — the J2 parity the two layers owe each
other). Two relevance gates, in order:

- **drop join-less repos** (iris#38 arm-1) — a repo with neither an open issue nor a referencing task
  participates in no join for this query; it is roster noise, not integral context.
- **scope task attribution to the named repos** (iris#38 arm-2) — a standing task that references N
  repos emits a ``has-task`` edge to each, so without scoping it SCATTERS: the repo shows under all N
  (e.g. ``^fl1p26`` naming ``iris`` + ``agent-kit`` surfaces agent-kit under an iris-only query). When
  the query NAMES repos as ``<repo>#<n>``, a repo stays only for an INDEPENDENT relevance reason — it
  is query-named, or it carries its own open issues — never merely because a multi-repo task also
  named it. (Today a repo's own issues already imply it was named, since the tracker scopes issues to
  the same ``repo_refs`` key, iris#36; the issues clause states that first-class relevance directly
  rather than leaning on that coincidence.) A query naming no repo has no scope signal, so arm-1 alone
  applies.
"""

from __future__ import annotations

from iris.core.compose import ComposedRepo, Composition
from iris.sources._repos import repo_refs


def relevant_repos(composition: Composition, task: str) -> list[ComposedRepo]:
    """The composed repos worth displaying for ``task`` — join-less and off-scope repos dropped."""
    scope = set(repo_refs(task))
    return [
        rw
        for rw in composition.repos
        if (rw.issues or rw.tasks) and (not scope or rw.repo.id in scope or bool(rw.issues))
    ]
