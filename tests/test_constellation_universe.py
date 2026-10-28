"""SP-T2 gate: on-disk roots for a universe-kind query, repo attrs, and the forge-slug identity."""

from __future__ import annotations

from pathlib import Path

from iris.core.source import KIND_NODES, KIND_UNIVERSE, Query
from iris.sources._repos import forge_slug
from iris.sources.constellation import ConstellationSource

UNIVERSE = Query(kinds=frozenset({KIND_UNIVERSE}))


def _checkout(path: Path, origin: str | None = None, catalog: str | None = None) -> Path:
    (path / ".git").mkdir(parents=True)
    if origin:
        (path / ".git" / "config").write_text(
            f'[core]\n\tbare = false\n[remote "origin"]\n\turl = {origin}\n\tfetch = +refs/heads/*\n',
            encoding="utf-8",
        )
    if catalog:
        (path / "catalog-info.yaml").write_text(catalog, encoding="utf-8")
    return path


def _source(tmp_path: Path, mrconfig_body: str = "", **opts) -> ConstellationSource:
    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(mrconfig_body, encoding="utf-8")
    return ConstellationSource("constellation", {"mrconfig": str(mrconfig), **opts})


def _repos(result) -> dict[str, dict]:
    return {n.attrs["path"]: n.attrs for n in result.nodes if n.kind == "repo"}


def test_universe_query_adds_checkouts_under_roots_within_depth(tmp_path) -> None:
    root = tmp_path / "src"
    _checkout(root / "a")
    _checkout(root / "group" / "b")
    _checkout(root / "x" / "y" / "too-deep")
    result = _source(tmp_path, roots=[str(root)], depth=2).read(UNIVERSE)
    repos = _repos(result)
    assert set(repos) == {str(root / "a"), str(root / "group" / "b")}
    assert all(a["origin"] == "disk" for a in repos.values())


def test_a_root_that_is_a_checkout_is_one(tmp_path) -> None:
    single = _checkout(tmp_path / "lonely")
    repos = _repos(_source(tmp_path, roots=[str(single)]).read(UNIVERSE))
    assert set(repos) == {str(single)}


def test_without_universe_the_repo_set_is_the_registry(tmp_path) -> None:
    registered = _checkout(tmp_path / "reg")
    root = tmp_path / "src"
    _checkout(root / "extra")
    body = f"[{registered}]\ncheckout = x\n"
    source = _source(tmp_path, body, roots=[str(root)])
    for query in (Query(), Query(kinds=frozenset({KIND_NODES}))):
        assert {n.id for n in source.read(query).nodes if n.kind == "repo"} == {"reg"}


def test_git_file_is_not_a_checkout_and_scan_skips_checkouts_and_worktrees(tmp_path) -> None:
    root = tmp_path / "src"
    linked = root / "linked"
    linked.mkdir(parents=True)
    (linked / ".git").write_text("gitdir: /elsewhere\n", encoding="utf-8")
    outer = _checkout(root / "outer")
    _checkout(outer / "nested")
    _checkout(root / "holder" / ".worktrees" / "wt")
    repos = _repos(_source(tmp_path, roots=[str(root)], depth=3).read(UNIVERSE))
    assert set(repos) == {str(outer)}


def test_missing_mrconfig_path_has_exists_false_and_slug_from_clone_url(tmp_path) -> None:
    gone = tmp_path / "gone"
    body = f"[{gone}]\ncheckout = git clone 'git@host.example:org/gone.git' 'gone'\n"
    attrs = _repos(_source(tmp_path, body).read(Query()))[str(gone)]
    assert attrs["exists"] is False
    assert attrs["origin"] == "mrconfig"
    assert attrs["slug"] == "host.example/org/gone"


def test_slug_comes_from_origin_not_the_directory_name(tmp_path) -> None:
    repo = _checkout(tmp_path / "other", origin="git@host.example:org/real-name.git")
    body = f"[{repo}]\ncheckout = x\n"
    attrs = _repos(_source(tmp_path, body).read(Query()))[str(repo)]
    assert attrs["slug"] == "host.example/org/real-name"
    assert attrs["exists"] is True


def test_slug_forms_and_host_aliases() -> None:
    assert forge_slug("https://host.example/org/sub/real-name.git") == "host.example/org/sub/real-name"
    assert forge_slug("ssh://git@Host.Example:2222/Org/X.git") == "host.example/org/x"
    assert forge_slug("git@gh-alias:org/x.git", {"gh-alias": "host.example"}) == "host.example/org/x"


def test_checkout_without_origin_is_local_basename(tmp_path) -> None:
    root = tmp_path / "src"
    repo = _checkout(root / "no-remote")
    attrs = _repos(_source(tmp_path, roots=[str(root)]).read(UNIVERSE))[str(repo)]
    assert attrs["slug"] == "local:no-remote"


def test_local_node_with_descriptor_carries_declared_name(tmp_path) -> None:
    root = tmp_path / "src"
    repo = _checkout(root / "dir", catalog="metadata:\n  name: declared\n")
    attrs = _repos(_source(tmp_path, roots=[str(root)]).read(UNIVERSE))[str(repo)]
    assert attrs["descriptor"] is True
    assert attrs["declared_name"] == "declared"


def test_universe_query_records_the_registry_it_read(tmp_path) -> None:
    scopes = [n for n in _source(tmp_path).read(UNIVERSE).nodes if n.kind == "scope"]
    assert [(n.attrs["dimension"], n.attrs["read"]) for n in scopes] == [("registry", True)]


def test_scan_does_not_follow_symlinks(tmp_path) -> None:
    real = _checkout(tmp_path / "elsewhere" / "target")
    root = tmp_path / "src"
    root.mkdir()
    (root / "link").symlink_to(real.parent, target_is_directory=True)
    (root / "repo-link").symlink_to(real, target_is_directory=True)
    assert _repos(_source(tmp_path, roots=[str(root)]).read(UNIVERSE)) == {}


def test_default_depth_is_two(tmp_path) -> None:
    root = tmp_path / "src"
    shallow = _checkout(root / "a" / "b")
    _checkout(root / "a" / "b2" / "c")
    assert set(_repos(_source(tmp_path, roots=[str(root)]).read(UNIVERSE))) == {str(shallow)}
