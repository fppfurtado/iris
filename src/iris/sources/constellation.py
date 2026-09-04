"""constellation source — repos + tags + relations from the interim source.

Reads the repo inventory from ``~/.mrconfig`` (realpath / symlink-aware, since the
file is often rendered by a dotfiles manager) and enriches each repo from its
``catalog-info.yaml`` (Backstage-style): ``metadata.tags`` → tags, ``spec.type`` →
roles, ``spec.dependsOn`` → relations. A repo without a ``catalog-info.yaml`` is
still returned as a node, and the result is flagged as incomplete-coverage.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from iris.core.model import Node, Relation
from iris.core.registry import DEFAULT
from iris.core.source import KIND_NODES, Query, Source, SourceResult
from iris.sources._repos import identity, repo_paths


def _node_from_catalog(name: str, catalog: Path) -> tuple[Node, list[Relation]]:
    # A catalog-info.yaml may be multi-document (`---`-separated entities); take the
    # first mapping document (the Component).
    docs = [d for d in yaml.safe_load_all(catalog.read_text(encoding="utf-8")) if isinstance(d, dict)]
    meta = docs[0] if docs else {}
    metadata = meta.get("metadata") or {}
    spec = meta.get("spec") or {}
    tags = list(metadata.get("tags") or [])
    roles = [spec["type"]] if spec.get("type") else []
    relations = [
        Relation(from_=name, type="dependsOn", to=str(dep))
        for dep in (spec.get("dependsOn") or [])
    ]
    node = Node(
        id=name,
        kind="repo",
        title=metadata.get("description") or name,
        tags=tags,
        roles=roles,
        source="constellation",
    )
    return node, relations


class ConstellationSource:
    """Reads the constellation (repos + tags + relations), read-only."""

    # Emits the node graph (nodes + relations); no hits.
    produces = frozenset({KIND_NODES})

    def __init__(self, name: str = "constellation", options: dict | None = None) -> None:
        opts = options or {}
        self.name = name
        self._mrconfig = opts.get("mrconfig", "~/.mrconfig")

    def read(self, query: Query) -> SourceResult:
        mrconfig = Path(os.path.realpath(os.path.expanduser(self._mrconfig)))
        repos = repo_paths(mrconfig)
        nodes: list[Node] = []
        relations: list[Relation] = []
        missing = 0
        for repo in repos:
            name = identity(repo)
            catalog = repo / "catalog-info.yaml"
            if catalog.is_file():
                node, rels = _node_from_catalog(name, catalog)
                nodes.append(node)
                relations.extend(rels)
            else:
                missing += 1
                nodes.append(Node(id=name, kind="repo", title=name, source="constellation"))
        note = ""
        if missing:
            note = f"incomplete-coverage: {missing}/{len(repos)} repos lack catalog-info.yaml"
        return SourceResult(nodes=nodes, relations=relations, ok=True, note=note)


def _factory(name: str, options: dict) -> Source:
    return ConstellationSource(name, options)


DEFAULT.register("constellation", _factory)
