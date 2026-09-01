"""The ``Source`` protocol — a read-only context source.

A source adapts one sovereign canonical (a knowledge base, a repo registry, …) into
iris's normalized model. Adding a source means writing one module that implements this
protocol and declaring it in ``sources.toml`` — no other module changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from iris.core.model import GroundHit, Node, Relation

# Result-kind labels — what a source can emit and what a caller consumes. Federation
# uses them to skip a source whose output the caller would only discard (kind-aware
# federation, iris#7). ``KIND_NODES`` covers the node graph — nodes *and* relations —
# since no command consumes relations independently today (grow a ``KIND_RELATIONS``
# by validated need, not ahead of one).
KIND_NODES = "nodes"
KIND_HITS = "hits"


@dataclass(frozen=True)
class Query:
    """A read request against sources.

    ``kinds`` declares which result-kinds the caller will consume (e.g.
    ``frozenset({KIND_NODES})`` for ``repos``); ``None`` means "all kinds", the
    federate-everything default. Federation skips a source whose declared ``produces``
    is disjoint from ``kinds`` — it would only contribute discarded results.
    """

    text: str = ""
    tag: str | None = None
    kinds: frozenset[str] | None = None


@dataclass
class SourceResult:
    """The normalized result of reading one source.

    ``ok=False`` with a ``note`` is how a source degrades gracefully: it returns empty
    plus a flag instead of raising, so one failing source never brings down the
    federation.
    """

    nodes: list[Node] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    hits: list[GroundHit] = field(default_factory=list)
    ok: bool = True
    note: str = ""


@runtime_checkable
class Source(Protocol):
    """A read-only context source. Implementations expose no write path."""

    name: str
    # The result-kinds this source can emit (e.g. ``frozenset({KIND_NODES})``). Lets
    # federation skip the source when a query wants none of them. A source that omits
    # it is treated as "undeclared" and is always read (backward-compatible).
    produces: frozenset[str]

    def read(self, query: Query) -> SourceResult:
        """Read this source for ``query`` and return a normalized result."""
        ...
