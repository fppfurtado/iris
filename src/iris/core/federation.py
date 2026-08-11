"""Federation — compose the declared sources into one read-only result.

This is where per-source isolation lives: each source is read independently and a
source that raises (or reports ``ok=False``) contributes a note instead of sinking
the whole federation (graceful degradation).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from iris.config import Config
from iris.core.model import GroundHit, Node, Relation
from iris.core.registry import DEFAULT, Registry
from iris.core.source import Query


@dataclass
class FederationResult:
    """The composed result across all federated sources."""

    nodes: list[Node] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    hits: list[GroundHit] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def federate(config: Config, query: Query, registry: Registry = DEFAULT) -> FederationResult:
    """Read every declared source and compose the results.

    A source that raises is isolated: its failure becomes a note and the other
    sources still contribute. Per-source coverage/degradation notes are collected too.
    """
    result = FederationResult()
    for source in registry.resolve(config):
        try:
            part = source.read(query)
        except Exception as exc:  # per-source isolation (PR5 cross-cutting)
            result.notes.append(f"{source.name}: failed ({exc})")
            continue
        result.nodes.extend(part.nodes)
        result.relations.extend(part.relations)
        result.hits.extend(part.hits)
        if part.note:
            result.notes.append(f"{source.name}: {part.note}")
        if not part.ok:
            result.notes.append(f"{source.name}: degraded")
    return result
