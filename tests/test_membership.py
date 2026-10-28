"""SP-T5 gate: compose_membership — one fixture per drift kind, plus the identity/degradation scenarios."""

from __future__ import annotations

from pathlib import Path

from iris.core.federation import FederationResult
from iris.core.membership import DRIFT_KINDS, compose_membership
from iris.core.model import Node

H = "forge.example"


def repo(path: str, slug: str, *, origin: str = "disk", descriptor: bool = False, declared: str | None = None,
         depends: tuple[str, ...] = (), exists: bool = True) -> Node:
    attrs: dict = {"path": path, "slug": slug, "origin": origin, "descriptor": descriptor,
                   "depends_on": list(depends)}
    if origin == "mrconfig":
        attrs["exists"] = exists
    if declared:
        attrs["declared_name"] = declared
    return Node(id=Path(path).name, kind="repo", title=path, attrs=attrs)


def reg(path: str, slug: str, **kw) -> Node:
    return repo(path, slug, origin="mrconfig", **kw)


def member(path: str, slug: str, **kw) -> Node:
    kw.setdefault("declared", slug.rsplit("/", 1)[-1])
    return reg(path, slug, descriptor=True, **kw)


def forge(slug: str, archived: bool = False) -> Node:
    return Node(id=slug.rsplit("/", 1)[-1], kind="repo", title=slug,
                attrs={"origin": "forge", "slug": slug, "archived": archived})


def fscope(org: str = "org", host: str = H, read: bool = True) -> Node:
    return Node(id=f"forge:{host}/{org}", kind="scope", title=f"{host}/{org}",
                attrs={"dimension": "forge", "host": host, "org": org, "read": read})


def rscope(root: str = "/r", read: bool = True) -> Node:
    return Node(id=f"roots:{root}", kind="scope", title=root, attrs={"dimension": "roots", "read": read})


def resource(rid: str, host_path: str, dependency_of: tuple[str, ...] = ()) -> Node:
    return Node(id=rid, kind="resource", title=rid,
                attrs={"host": Path(host_path).name, "host_path": host_path, "dependency_of": list(dependency_of)})


def base(*extra: Node, app: Node | None = None) -> list[Node]:
    return [rscope(), fscope(), app or member("/r/app", f"{H}/org/app"), forge(f"{H}/org/app"), *extra]


def run(nodes: list[Node], check: dict | None = None):
    return compose_membership(FederationResult(nodes=nodes), check or {})


def of(report, kind: str) -> list:
    return [i for i in report.items if i.kind == kind]


def test_fully_consistent_constellation_has_no_items() -> None:
    report = run(base())
    assert report.items == []
    assert report.skipped == []


def _exactly_one(report, kind: str, subject: str) -> None:
    hits = of(report, kind)
    assert [i.subject for i in hits] == [subject], report.items


def test_undeclared_member() -> None:
    _exactly_one(run(base(repo("/r/bare", f"{H}/org/bare"), forge(f"{H}/org/bare"))),
                 "undeclared-member", f"{H}/org/bare")


def test_uncloned() -> None:
    _exactly_one(run(base(forge(f"{H}/org/new"))), "uncloned", f"{H}/org/new")


def test_stale_remote() -> None:
    _exactly_one(run(base(member("/r/old", f"{H}/org/old"))), "stale-remote", f"{H}/org/old")


def test_phantom() -> None:
    nodes = base(reg("/r/missing", f"{H}/org/missing", exists=False), forge(f"{H}/org/missing"))
    _exactly_one(run(nodes), "phantom", "/r/missing")


def test_unregistered() -> None:
    nodes = base(repo("/r/loose", f"{H}/org/loose", descriptor=True, declared="loose"), forge(f"{H}/org/loose"))
    _exactly_one(run(nodes), "unregistered", f"{H}/org/loose")


def test_archived_registered() -> None:
    nodes = base(member("/r/old", f"{H}/org/old"), forge(f"{H}/org/old", archived=True))
    _exactly_one(run(nodes), "archived-registered", f"{H}/org/old")


def test_archived_host() -> None:
    nodes = base(member("/r/host", f"{H}/org/host"), forge(f"{H}/org/host", archived=True),
                 resource("db", "/r/host"))
    _exactly_one(run(nodes), "archived-host", "db")


def test_dangling_dependency() -> None:
    app = member("/r/app", f"{H}/org/app", depends=("resource:nope",))
    _exactly_one(run(base(app=app)), "dangling-dependency", "nope")


def test_one_end_only() -> None:
    app = member("/r/app", f"{H}/org/app", depends=("resource:db",))
    _exactly_one(run(base(resource("db", "/r/app"), app=app)), "one-end-only", "db")


def test_name_mismatch() -> None:
    app = member("/r/app", f"{H}/org/app", declared="old-name")
    _exactly_one(run(base(app=app)), "name-mismatch", f"{H}/org/app")


def test_exclusion_invalid() -> None:
    _exactly_one(run(base(), {"exclude": {f"{H}/org/ghost": "study"}}), "exclusion-invalid", f"{H}/org/ghost")
    _exactly_one(run(base(), {"exclude": {f"{H}/org/app": " "}}), "exclusion-invalid", f"{H}/org/app")


def test_exclusion_promoted() -> None:
    _exactly_one(run(base(), {"exclude": {f"{H}/org/app": "study"}}), "exclusion-promoted", f"{H}/org/app")


def test_mirror_missing(tmp_path) -> None:
    mirror = tmp_path / "list.md"
    mirror.write_text("nothing listed\n", encoding="utf-8")
    check = {"mirrors": [{"path": str(mirror), "pattern": "`([a-z0-9._-]+)`"}]}
    _exactly_one(run(base(), check), "mirror-missing", "app")


def test_mirror_stale(tmp_path) -> None:
    mirror = tmp_path / "list.md"
    mirror.write_text("- `app`\n- `ghost`\n- ~~`gone`~~\n", encoding="utf-8")
    check = {"mirrors": [{"path": str(mirror), "pattern": r"(?<!~~)`([a-z0-9][a-z0-9._-]*)`(?!~~)"}]}
    _exactly_one(run(base(), check), "mirror-stale", "ghost")


def test_duplicate_identity() -> None:
    copy = repo("/elsewhere/app-copy", f"{H}/org/app", descriptor=True, declared="app")
    _exactly_one(run(base(copy)), "duplicate-identity", f"{H}/org/app")


def test_every_kind_has_a_case() -> None:
    names = {n.removeprefix("test_").replace("_", "-") for n in globals() if n.startswith("test_")}
    assert set(DRIFT_KINDS) <= names
    assert len(DRIFT_KINDS) == 15


# --- scenarios ------------------------------------------------------------------------------------

def test_basename_differing_from_slug_name_joins_by_slug() -> None:
    nodes = base(member("/r/dir-name", f"{H}/org/real"), forge(f"{H}/org/real"))
    report = run(nodes)
    assert of(report, "uncloned") == []
    assert not any("dir-name" in i.subject for i in report.items)


def test_rename_shows_stale_remote_and_uncloned_naming_it() -> None:
    report = run(base(member("/r/old", f"{H}/org/old"), forge(f"{H}/org/new")))
    _exactly_one(report, "stale-remote", f"{H}/org/old")
    uncloned = of(report, "uncloned")
    assert [i.subject for i in uncloned] == [f"{H}/org/new"]
    assert f"{H}/org/old" in uncloned[0].detail


def test_same_basename_under_two_roots_resolves_resource_host_by_path() -> None:
    a = member("/a/tool", f"{H}/org/tool")
    b = member("/b/tool", f"{H}/other/tool", depends=("resource:db",))
    common = base(fscope("other"), rscope("/a"), rscope("/b"), a, b,
                  forge(f"{H}/org/tool", archived=True), forge(f"{H}/other/tool"))
    on_live = run([*common, resource("db", "/b/tool", ("tool",))])
    assert of(on_live, "archived-host") == []
    assert of(on_live, "one-end-only") == []
    on_archived = run([*common, resource("db", "/a/tool")])
    _exactly_one(on_archived, "archived-host", "db")
    _exactly_one(on_archived, "one-end-only", "db")


def test_subgroup_path_matches() -> None:
    report = run(base(fscope("group"), member("/r/x", f"{H}/group/sub/x"), forge(f"{H}/group/sub/x")))
    assert of(report, "uncloned") == [] and of(report, "stale-remote") == []


def test_one_name_on_two_forges_is_two_identities() -> None:
    other = "other.example"
    report = run(base(fscope("org2", host=other), forge(f"{other}/org2/app")))
    assert of(report, "duplicate-identity") == []
    assert [i.subject for i in of(report, "uncloned")] == [f"{other}/org2/app"]


def test_resource_consumers_without_dependency_of_yield_one_item_each() -> None:
    app = member("/r/app", f"{H}/org/app", depends=("resource:db",))
    other = member("/r/other", f"{H}/org/other", depends=("resource:db",))
    report = run(base(other, forge(f"{H}/org/other"), resource("db", "/r/app"), app=app))
    hits = of(report, "one-end-only")
    assert len(hits) == 2
    assert {h.detail.split()[0] for h in hits} == {"app", "other"}


def test_forge_skipped_treats_every_local_repo_as_live() -> None:
    nodes = [rscope(), member("/r/app", f"{H}/org/app")]
    report = run(nodes)
    assert any(s.startswith("forge") for s in report.skipped)
    assert report.counts["members"] == 1
    assert report.items == []


def test_archived_repo_never_yields_membership_kinds(tmp_path) -> None:
    mirror = tmp_path / "list.md"
    mirror.write_text("`app`\n", encoding="utf-8")
    nodes = base(
        repo("/r/bare", f"{H}/org/bare"), forge(f"{H}/org/bare", archived=True),
        forge(f"{H}/org/far", archived=True),
        repo("/r/loose", f"{H}/org/loose", descriptor=True, declared="loose"), forge(f"{H}/org/loose", archived=True),
    )
    report = run(nodes, {"mirrors": [{"path": str(mirror), "pattern": "`([a-z]+)`"}]})
    for kind in ("undeclared-member", "uncloned", "unregistered", "mirror-missing"):
        assert of(report, kind) == [], kind


def test_unused_resource_is_not_drift() -> None:
    assert run(base(resource("idle", "/r/app"))).items == []


def test_incomplete_forge_bounds_comparisons_to_the_orgs_read() -> None:
    nodes = base(fscope("org2", read=False), member("/r/z", f"{H}/org2/z"))
    report = run(nodes, {"exclude": {f"{H}/org2/ghost": "study"}})
    assert any(s.startswith("forge") for s in report.skipped)
    assert of(report, "stale-remote") == []
    assert of(report, "exclusion-invalid") == []


def test_unreadable_mirror_is_skipped(tmp_path) -> None:
    missing = tmp_path / "nope.md"
    report = run(base(), {"mirrors": [{"path": str(missing), "pattern": "`([a-z]+)`"}]})
    assert any(str(missing) in s for s in report.skipped)
    assert of(report, "mirror-missing") == [] and of(report, "mirror-stale") == []


def test_host_aliases_map_local_slugs_onto_the_forge_host() -> None:
    app = member("/r/app", "gh-alias/org/app")
    report = run(base(app=app), {"host_aliases": {"gh-alias": H}})
    assert report.items == []
