"""constellation source — repos, the resources they host, tags and relations from the repo registry.

Reads the repo inventory from ``~/.mrconfig`` (realpath / symlink-aware, since the file is often rendered
by a dotfiles manager) and enriches each repo from its ``catalog-info.yaml`` (Backstage-style, parsed by
``_catalog``): the Component's ``metadata.tags`` → tags, ``spec.type`` → roles, and each ``spec.dependsOn``
ref → a ``dependsOn`` relation (the raw ref also kept in ``attrs.depends_on``). Every ``kind: Resource``
document becomes a ``resource`` node hosted by the repo (a ``hosted-by`` relation; ``attrs.host`` /
``attrs.host_path`` name the host, ``attrs.dependency_of`` its declared consumers). A repo without a
``catalog-info.yaml`` is still returned as a node, and the result is flagged as incomplete-coverage.

Each repo node carries the facts a membership check joins on (``attrs``): its local ``path``, whether it
has a ``descriptor``, its ``origin`` (``mrconfig`` | ``disk``), ``exists`` for registry entries, its forge
``slug`` (from the checkout's ``origin`` remote, or from the clone URL of an uncloned registry entry; see
``_repos.local_slug``) and the descriptor's ``declared_name``. Node ids stay the checkout basename.

On a query whose kinds include ``universe``, the source also scans the configured on-disk ``roots`` (up to
``depth`` levels, default 2) and adds every checkout found there with ``origin="disk"``: a directory is a
checkout iff it holds a ``.git`` directory (a ``.git`` file is a linked worktree, skipped); the scan never
descends into a checkout or a ``.worktrees`` directory and follows no symlink; a root that is itself a
checkout counts as one. It also emits one ``scope`` node per configured root (``attrs.read`` says whether
the root could be scanned), so a composer can tell an unscanned dimension from an empty one. Without
``universe`` the scan never runs and the repo set is the registry's alone.
"""

from __future__ import annotations

import os
from pathlib import Path

from iris.core.model import Node, Relation
from iris.core.registry import DEFAULT
from iris.core.source import KIND_NODES, KIND_UNIVERSE, Query, Source, SourceResult
from iris.sources._catalog import parse_descriptor, parse_entity_ref
from iris.sources._repos import identity, local_slug, repo_entries

_DEFAULT_DEPTH = 2


def _nodes_from_catalog(
    name: str, repo: Path, catalog: Path, source: str, attrs: dict
) -> tuple[Node, list[Node], list[Relation]]:
    """The repo node, its resource nodes, and their relations, from one descriptor."""
    descriptor = parse_descriptor(catalog)
    metadata = descriptor.component.get("metadata") or {}
    spec = descriptor.component.get("spec") or {}
    node_attrs = {**attrs, "descriptor": True, "depends_on": list(descriptor.depends_on)}
    if metadata.get("name"):
        node_attrs["declared_name"] = str(metadata["name"])
    node = Node(
        id=name,
        kind="repo",
        title=metadata.get("description") or name,
        tags=list(metadata.get("tags") or []),
        roles=[spec["type"]] if spec.get("type") else [],
        source=source,
        attrs=node_attrs,
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


def _is_checkout(path: Path) -> bool:
    return (path / ".git").is_dir()


def _scan(root: Path, depth: int) -> list[Path]:
    """Every checkout under ``root`` within ``depth`` levels (``root`` itself when it is one)."""
    if _is_checkout(root):
        return [root]
    found: list[Path] = []
    level = [root]
    for _ in range(depth):
        nxt: list[Path] = []
        for directory in level:
            try:
                entries = sorted(os.scandir(directory), key=lambda e: e.name)
            except OSError:
                continue
            for entry in entries:
                if entry.name == ".worktrees" or not entry.is_dir(follow_symlinks=False):
                    continue
                path = Path(entry.path)
                if _is_checkout(path):
                    found.append(path)
                else:
                    nxt.append(path)
        level = nxt
    return found


class ConstellationSource:
    """Reads the constellation (repos + resources + tags + relations), read-only."""

    # Emits the node graph (nodes + relations), and widens the repo set beyond the registry for a
    # universe-kind query; no hits.
    produces = frozenset({KIND_NODES, KIND_UNIVERSE})

    def __init__(self, name: str = "constellation", options: dict | None = None) -> None:
        opts = options or {}
        self.name = name
        self._mrconfig = opts.get("mrconfig", "~/.mrconfig")
        self._roots: list[str] = list(opts.get("roots", []))
        self._depth = int(opts.get("depth", _DEFAULT_DEPTH))

    def read(self, query: Query) -> SourceResult:
        mrconfig = Path(os.path.realpath(os.path.expanduser(self._mrconfig)))
        entries = repo_entries(mrconfig)
        nodes: list[Node] = []
        relations: list[Relation] = []
        missing = 0
        for repo, checkout in entries:
            attrs = {
                "path": str(repo),
                "descriptor": False,
                "origin": "mrconfig",
                "exists": repo.is_dir(),
                "slug": local_slug(repo, checkout),
            }
            if not self._add_repo(repo, attrs, nodes, relations):
                missing += 1
        if query.kinds is not None and KIND_UNIVERSE in query.kinds:
            registered = {os.path.realpath(repo) for repo, _ in entries}
            for root_opt in self._roots:
                root = Path(os.path.expanduser(root_opt))
                nodes.append(
                    Node(
                        id=f"roots:{root}",
                        kind="scope",
                        title=str(root),
                        source=self.name,
                        attrs={"dimension": "roots", "read": root.is_dir()},
                    )
                )
                if not root.is_dir():
                    continue
                for repo in _scan(root, self._depth):
                    real = os.path.realpath(repo)
                    if real in registered:
                        continue
                    registered.add(real)
                    attrs = {"path": str(repo), "descriptor": False, "origin": "disk", "slug": local_slug(repo)}
                    self._add_repo(repo, attrs, nodes, relations)
        note = ""
        if missing:
            note = f"incomplete-coverage: {missing}/{len(entries)} repos lack catalog-info.yaml"
        return SourceResult(nodes=nodes, relations=relations, ok=True, note=note)

    def _add_repo(self, repo: Path, attrs: dict, nodes: list[Node], relations: list[Relation]) -> bool:
        """Append ``repo``'s nodes and relations; return whether it carries a descriptor."""
        name = identity(repo)
        catalog = repo / "catalog-info.yaml"
        if catalog.is_file():
            node, resources, rels = _nodes_from_catalog(name, repo, catalog, "constellation", attrs)
            nodes.append(node)
            nodes.extend(resources)
            relations.extend(rels)
            return True
        nodes.append(Node(id=name, kind="repo", title=name, source="constellation", attrs=attrs))
        return False


def _factory(name: str, options: dict) -> Source:
    return ConstellationSource(name, options)


DEFAULT.register("constellation", _factory)
