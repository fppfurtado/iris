"""Constellation membership & drift — the cross-source composition behind ``iris check`` (iris#48).

Composes a universe-kind federation result (registry + on-disk checkouts from the constellation source,
forge listings from ``forge-repos`` sources) with the ``[check]`` config table into a :class:`DriftReport`:
a closed set of drift kinds plus the dimensions that could not run. Pure except for reading mirror files.

Every identity join is by forge slug (``attrs.slug``), with hosts mapped through ``check.host_aliases``;
local repos are joined by ``attrs.path``, never by node id (a basename is not unique across roots). A
member is a local checkout carrying a descriptor; a slug the forge reports archived is never a live member.
A dimension that could not run is listed in ``skipped`` and never folded into "clean" (fail-honest).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from iris.core.federation import FederationResult
from iris.core.model import Node
from iris.sources._catalog import parse_entity_ref

# The closed set of drift kinds, in report order.
DRIFT_KINDS = (
    "undeclared-member",
    "uncloned",
    "stale-remote",
    "phantom",
    "unregistered",
    "archived-registered",
    "archived-host",
    "dangling-dependency",
    "one-end-only",
    "name-mismatch",
    "exclusion-invalid",
    "exclusion-promoted",
    "mirror-missing",
    "mirror-stale",
    "duplicate-identity",
)


@dataclass(frozen=True)
class DriftItem:
    """One drift finding: its ``kind`` (from :data:`DRIFT_KINDS`), the ``subject`` it is about, a ``detail``."""

    kind: str
    subject: str
    detail: str


@dataclass
class DriftReport:
    """The check's result: drift items, the dimensions that could not run (with why), and counts."""

    items: list[DriftItem] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)


def _name(slug: str) -> str:
    """An identity's name — the last segment of its slug (``local:<basename>`` → the basename)."""
    return slug.rsplit("/", 1)[-1].removeprefix("local:")


def _alias(slug: str, aliases: dict[str, str]) -> str:
    if slug.startswith("local:") or "/" not in slug:
        return slug
    host, path = slug.split("/", 1)
    return f"{aliases.get(host, host)}/{path}"


def compose_membership(result: FederationResult, check: dict) -> DriftReport:
    """Compute every drift kind over a universe-kind federation result (see the module docstring)."""
    aliases = {str(k).lower(): str(v).lower() for k, v in (check.get("host_aliases") or {}).items()}
    exclude = {str(k).lower(): str(v) for k, v in (check.get("exclude") or {}).items()}
    report = DriftReport()
    items: list[DriftItem] = []

    def slug_of(node: Node) -> str:
        return _alias(str(node.attrs.get("slug", f"local:{node.id}")), aliases)

    repos = [n for n in result.nodes if n.kind == "repo"]
    resources = [n for n in result.nodes if n.kind == "resource"]
    scopes = [n for n in result.nodes if n.kind == "scope"]

    registry = [n for n in repos if n.attrs.get("origin") == "mrconfig"]
    local = [
        n for n in repos
        if n.attrs.get("origin") == "disk" or (n.attrs.get("origin") == "mrconfig" and n.attrs.get("exists"))
    ]
    forge = [n for n in repos if n.attrs.get("origin") == "forge"]

    # --- dimensions --------------------------------------------------------------------------------
    # Every kind rests on the registry read: without it the local universe is unknown, so any item would
    # be computed against an empty side (e.g. every mirror name reported stale). Report nothing instead.
    if not any(s.attrs.get("dimension") == "registry" and s.attrs.get("read") for s in scopes):
        report.skipped.append("registry — the repo registry was not read (see the source notes); no drift computed")
        report.counts = dict.fromkeys(("members", "archived", "excluded", "resources", "dependencies"), 0)
        return report
    forge_scopes = [s for s in scopes if s.attrs.get("dimension") == "forge"]
    read_scopes = {
        (s.attrs.get("host", ""), s.attrs.get("org", "")) for s in forge_scopes if s.attrs.get("read")
    }
    read_scopes = {(aliases.get(h, h), o) for h, o in read_scopes}
    unread = [s.title for s in forge_scopes if not s.attrs.get("read")]
    forge_complete = bool(forge_scopes) and not unread
    if not forge_scopes:
        report.skipped.append(
            "forge — no forge-repos source read (none configured, or it failed — see the source notes); "
            "archived state unknown, every local repo treated as live"
        )
    elif unread:
        report.skipped.append(f"forge — incomplete, not read: {', '.join(unread)}; forge comparisons bounded to the orgs read")

    root_scopes = [s for s in scopes if s.attrs.get("dimension") == "roots"]
    unread_roots = [s.title for s in root_scopes if not s.attrs.get("read")]
    roots_complete = bool(root_scopes) and not unread_roots
    if not root_scopes:
        report.skipped.append("roots — no roots configured; `uncloned` needs the local universe beyond the registry")
    elif unread_roots:
        report.skipped.append(f"roots — not readable: {', '.join(unread_roots)}; `uncloned` not computed")

    def in_read_scope(slug: str) -> tuple[str, str] | None:
        for host, org in read_scopes:
            if slug.startswith(f"{host}/{org}/"):
                return host, org
        return None

    # --- identity indexes --------------------------------------------------------------------------
    forge_archived = {slug_of(n): bool(n.attrs.get("archived")) for n in forge}
    archived = {s for s, a in forge_archived.items() if a}
    registry_slugs = {slug_of(n) for n in registry}
    local_by_slug: dict[str, list[Node]] = {}
    for n in local:
        local_by_slug.setdefault(slug_of(n), []).append(n)
    local_by_path = {str(n.attrs.get("path")): n for n in local}
    members = [n for n in local if n.attrs.get("descriptor") and slug_of(n) not in archived]

    # --- local / registry kinds --------------------------------------------------------------------
    for n in local:
        slug = slug_of(n)
        if not n.attrs.get("descriptor") and slug not in exclude and slug not in archived:
            items.append(DriftItem("undeclared-member", slug, f"no catalog-info.yaml at {n.attrs.get('path')}"))
    for n in registry:
        if not n.attrs.get("exists"):
            items.append(DriftItem("phantom", str(n.attrs.get("path")), "registry entry path does not exist"))
    for n in members:
        slug = slug_of(n)
        if slug not in registry_slugs:
            items.append(DriftItem("unregistered", slug, f"member at {n.attrs.get('path')} has no registry entry"))
        declared = n.attrs.get("declared_name")
        if declared and declared != _name(slug):
            items.append(DriftItem("name-mismatch", slug, f"descriptor metadata.name is {declared!r}"))
    for slug, nodes in local_by_slug.items():
        paths = sorted({str(n.attrs.get("path")) for n in nodes})
        if len(paths) > 1 and not slug.startswith("local:"):
            items.append(DriftItem("duplicate-identity", slug, f"resolved by {', '.join(paths)}"))

    # --- forge kinds -------------------------------------------------------------------------------
    stale_by_scope: dict[tuple[str, str], list[str]] = {}
    for slug, nodes in local_by_slug.items():
        scope = in_read_scope(slug)
        if scope and slug not in forge_archived:
            stale_by_scope.setdefault(scope, []).append(slug)
            paths = ", ".join(sorted(str(n.attrs.get("path")) for n in nodes))
            items.append(DriftItem("stale-remote", slug, f"the forge does not list it (checkout at {paths})"))
    if roots_complete:
        for n in forge:
            slug = slug_of(n)
            if slug in archived or slug in exclude or slug in local_by_slug or slug in registry_slugs:
                continue
            detail = "on the forge, no local checkout or registry entry"
            stale = stale_by_scope.get(in_read_scope(slug) or ("", ""), [])
            if stale:
                detail += f"; stale-remote under the same host+org: {', '.join(sorted(stale))} (possibly a rename)"
            items.append(DriftItem("uncloned", slug, detail))
    for slug in sorted(archived & registry_slugs):
        items.append(DriftItem("archived-registered", slug, "the forge reports it archived"))

    # --- resource kinds ----------------------------------------------------------------------------
    declared_resources = {r.id: r for r in resources}
    for r in resources:
        host = local_by_path.get(str(r.attrs.get("host_path")))
        if host is not None and slug_of(host) in archived:
            items.append(DriftItem("archived-host", r.id, f"host repo {slug_of(host)} is archived"))
    consumers: dict[str, set[str]] = {}
    dependencies = 0
    for n in members:
        entity = str(n.attrs.get("declared_name") or _name(slug_of(n)))
        for ref in n.attrs.get("depends_on") or []:
            kind, _, target = parse_entity_ref(ref)
            if kind != "resource":
                continue
            dependencies += 1
            if target not in declared_resources:
                items.append(DriftItem("dangling-dependency", target, f"{entity} depends on undeclared resource:{target}"))
            else:
                consumers.setdefault(target, set()).add(entity)
    for rid, r in declared_resources.items():
        declared_consumers = set(r.attrs.get("dependency_of") or [])
        using = consumers.get(rid, set())
        for c in sorted(using - declared_consumers):
            items.append(DriftItem("one-end-only", rid, f"{c} declares dependsOn but the host's dependencyOf omits it"))
        for c in sorted(declared_consumers - using):
            items.append(DriftItem("one-end-only", rid, f"dependencyOf lists {c}, which declares no dependsOn"))

    # --- exclusions --------------------------------------------------------------------------------
    universe = set(local_by_slug) | registry_slugs | set(forge_archived)
    for slug, reason in exclude.items():
        if not reason.strip():
            items.append(DriftItem("exclusion-invalid", slug, "empty reason"))
        elif slug not in universe and forge_complete:
            items.append(DriftItem("exclusion-invalid", slug, "names no repo in the universe"))
        if any(n.attrs.get("descriptor") for n in local_by_slug.get(slug, [])):
            items.append(DriftItem("exclusion-promoted", slug, "excluded, but its checkout carries a descriptor"))

    # --- mirrors -----------------------------------------------------------------------------------
    live_names = {_name(slug_of(n)) for n in members}
    for mirror in check.get("mirrors") or []:
        path = str(mirror.get("path", ""))
        try:
            text = Path(os.path.expanduser(path)).read_text(encoding="utf-8")
            listed = {m.group(1) for m in re.finditer(str(mirror.get("pattern", "")), text)}
        except (OSError, re.error, IndexError) as exc:
            report.skipped.append(f"mirror {path} — unreadable ({exc})")
            continue
        for name in sorted(live_names - listed):
            items.append(DriftItem("mirror-missing", name, f"not listed in {path}"))
        for name in sorted(listed - live_names):
            items.append(DriftItem("mirror-stale", name, f"listed in {path} but no live member has that name"))

    order = {k: i for i, k in enumerate(DRIFT_KINDS)}
    report.items = sorted(items, key=lambda i: (order[i.kind], i.subject, i.detail))
    report.counts = {
        "members": len(members),
        "archived": len(archived),
        "excluded": len(exclude),
        "resources": len(declared_resources),
        "dependencies": dependencies,
    }
    return report
