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

from typing import Callable

from iris.core.compose import ComposedRepo, Composition, InboundContext, compose_inbound
from iris.core.federation import FederationResult
from iris.core.registry import DEFAULT, Registry
from iris.core.source import KIND_CHAIN, KIND_INBOUND, Query
from iris.sources._repos import repo_refs


def relevant_repos(composition: Composition, task: str) -> list[ComposedRepo]:
    """The composed repos worth displaying for ``task`` — join-less and off-scope repos dropped."""
    scope = set(repo_refs(task))
    return [
        rw
        for rw in composition.repos
        if (rw.issues or rw.tasks) and (not scope or rw.repo.id in scope or bool(rw.issues))
    ]


def inbound_sources(config, registry: Registry = DEFAULT) -> list[str]:
    """The names of the configured sources that read ``inbound`` (their ``produces`` contains it)."""
    return [
        source.name
        for source in registry.resolve(config)
        if KIND_INBOUND in (getattr(source, "produces", None) or frozenset())
    ]


def inbound_context(config, key: str, federate: Callable[..., FederationResult]) -> InboundContext:
    """The ``iris inbound`` read, shared by the CLI and the MCP adapter (parity by construction).

    Three passes (Spec v2): the item's live state (``chain`` on the key), the records citing it
    (``inbound`` on the key — the store names the citing tasks by anchor), and, only when ≥1 task cites
    it, the state of those tasks (``chain`` on their anchors). ``federate`` is passed in so each surface
    keeps its own seam.
    """
    state = federate(config, Query(text=key, kinds=frozenset({KIND_CHAIN})))
    citing = federate(config, Query(text=key, kinds=frozenset({KIND_INBOUND})))
    anchors = list(dict.fromkeys(n.id for n in citing.nodes if n.kind == "task"))
    task_state = None
    if anchors:
        text = " ".join(f"^{anchor}" for anchor in anchors)
        task_state = federate(config, Query(text=text, kinds=frozenset({KIND_CHAIN})))
    return compose_inbound(key, state, citing, task_state, searched=inbound_sources(config))
