"""constellation source — repos, the resources they host, tags and relations from the repo registry.

Reads the repo inventory from ``~/.mrconfig`` (realpath / symlink-aware, since the file is often rendered
by a dotfiles manager) and enriches each repo from its ``catalog-info.yaml`` (Backstage-style, parsed by
``_catalog``): the Component's ``metadata.tags`` → tags, ``spec.type`` → roles, and each ``spec.dependsOn``
ref → a ``dependsOn`` relation (the raw ref also kept in ``attrs.depends_on``). Every ``kind: Resource``
document becomes a ``resource`` node hosted by the repo (a ``hosted-by`` relation; ``attrs.host`` /
``attrs.host_path`` name the host, ``attrs.dependency_of`` its declared consumers). A repo without a
``catalog-info.yaml`` is still returned as a node, and the result is flagged as incomplete-coverage.
"""

from __future__ import annotations

import os
from pathlib import Path

from iris.core.model import Node, Relation
from iris.core.registry import DEFAULT
from iris.core.source import KIND_NODES, Query, Source, SourceResult
from iris.sources._catalog import parse_descriptor, parse_entity_ref
from iris.sources._repos import identity, repo_paths


def _nodes_from_catalog(
    name: str, repo: Path, catalog: Path, source: str
) -> tuple[Node, list[Node], list[Relation]]:
    """The repo node, its resource nodes, and their relations, from one descriptor."""
    descriptor = parse_descriptor(catalog)
    metadata = descriptor.component.get("metadata") or {}
    spec = descriptor.component.get("spec") or {}
    node = Node(
        id=name,
        kind="repo",
        title=metadata.get("description") or name,
        tags=list(metadata.get("tags") or []),
        roles=[spec["type"]] if spec.get("type") else [],
        source=source,
        attrs={"depends_on": list(descriptor.depends_on)},
    )
    relations = [Relation(from_=name, type="dependsOn", to=dep) for dep in descriptor.depends_on]
    resources: list[Node] = []
    for doc in descriptor.resources:
        res_meta = doc.get("metadata") or {}
        res_spec = doc.get("spec") or {}
        res_id = str(res_meta.get("name") or "")
        if not res_id:
            continue
        resources.append(
            Node(
                id=res_id,
                kind="resource",
                title=res_meta.get("description") or res_id,
                roles=[res_spec["type"]] if res_spec.get("type") else [],
                source=source,
                attrs={
                    "host": name,
                    "host_path": str(repo),
                    "dependency_of": [
                        parse_entity_ref(ref)[2] for ref in (res_spec.get("dependencyOf") or [])
                    ],
                },
            )
        )
        relations.append(Relation(from_=res_id, type="hosted-by", to=name))
    return node, resources, relations


class ConstellationSource:
    """Reads the constellation (repos + resources + tags + relations), read-only."""

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
                node, resources, rels = _nodes_from_catalog(name, repo, catalog, "constellation")
                nodes.append(node)
                nodes.extend(resources)
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
