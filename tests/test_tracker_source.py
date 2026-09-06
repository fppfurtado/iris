"""SP-T1 acceptance — the `tracker` source emits issue nodes + repo->issue relations, one forge
invocation per repo checkout, and degrades a failing repo without sinking the read.

The fan-out is scoped by the query (iris#36): each read below cites the repos it wants as `<repo>#<n>`
in the query text; a query naming no repo spawns nothing (its own tests at the bottom)."""

from __future__ import annotations

from pathlib import Path

from iris.core.source import KIND_NODES, Query
from iris.sources.tracker import TrackerSource


def _mrconfig(tmp_path: Path, *repos: str) -> tuple[Path, list[Path]]:
    lines = ["[DEFAULT]", "git_gc = git gc"]
    paths = []
    for r in repos:
        p = tmp_path / r
        p.mkdir()
        paths.append(p)
        lines.append(f"[{p}]")
    cfg = tmp_path / ".mrconfig"
    cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return cfg, paths


def test_emits_issue_nodes_and_relations_one_call_per_checkout(tmp_path):
    cfg, _ = _mrconfig(tmp_path, "alpha", "beta")
    calls: list[str] = []

    def runner(cmd, cwd):
        calls.append(Path(cwd).name)
        if Path(cwd).name == "alpha":
            return '[{"number": 1, "title": "fix bug"}, {"number": 2, "title": "add flag"}]'
        return '[{"number": 7, "title": "beta thing"}]'

    src = TrackerSource("tracker", {"mrconfig": str(cfg), "command": ["gh", "issue", "list"]}, runner=runner)
    res = src.read(Query(text="work on alpha#1 and beta#7", kinds=frozenset({KIND_NODES})))

    assert res.ok
    assert sorted(n.id for n in res.nodes) == ["alpha#1", "alpha#2", "beta#7"]
    assert all(n.kind == "issue" for n in res.nodes)
    assert {n.title for n in res.nodes} == {"fix bug", "add flag", "beta thing"}
    rels = {(r.from_, r.type, r.to) for r in res.relations}
    assert ("alpha", "has-open-issue", "alpha#1") in rels
    assert ("beta", "has-open-issue", "beta#7") in rels
    # resolved by running the forge CLI once per repo checkout (cwd)
    assert sorted(calls) == ["alpha", "beta"]


def test_degrades_failing_repo_without_sinking(tmp_path):
    cfg, _ = _mrconfig(tmp_path, "alpha", "beta")

    def runner(cmd, cwd):
        if Path(cwd).name == "beta":
            raise RuntimeError("gh: not authenticated")
        return '[{"number": 1, "title": "ok"}]'

    src = TrackerSource("tracker", {"mrconfig": str(cfg), "command": ["gh", "issue", "list"]}, runner=runner)
    res = src.read(Query(text="touch alpha#1 and beta#1", kinds=frozenset({KIND_NODES})))

    assert not res.ok
    assert "1/2 repos unreadable" in res.note
    assert [n.id for n in res.nodes] == ["alpha#1"]  # the healthy repo still contributed


def test_nested_items_path_and_field_map(tmp_path):
    cfg, _ = _mrconfig(tmp_path, "alpha")

    def runner(cmd, cwd):
        return '{"data": {"issues": [{"iid": 9, "name": "glab-style"}]}}'

    src = TrackerSource(
        "tracker",
        {
            "mrconfig": str(cfg),
            "command": ["glab", "issue", "list"],
            "items": "data.issues",
            "map": {"number": "iid", "title": "name"},
        },
        runner=runner,
    )
    res = src.read(Query(text="alpha#9", kinds=frozenset({KIND_NODES})))
    assert [n.id for n in res.nodes] == ["alpha#9"]
    assert res.nodes[0].title == "glab-style"


def test_unexpected_shape_degrades_instead_of_malformed_nodes(tmp_path):
    # a wrapped object with `items` mis-configured (unset) must NOT iterate dict keys into `#None` nodes
    cfg, _ = _mrconfig(tmp_path, "alpha")

    def runner(cmd, cwd):
        return '{"data": {"issues": [{"number": 1, "title": "t"}]}}'  # a dict, but items path unset

    src = TrackerSource("tracker", {"mrconfig": str(cfg), "command": ["gh"]}, runner=runner)
    res = src.read(Query(text="alpha#1", kinds=frozenset({KIND_NODES})))
    assert res.nodes == []
    assert not res.ok
    assert "unexpected-shape" in res.note


def test_issue_without_number_is_skipped(tmp_path):
    cfg, _ = _mrconfig(tmp_path, "alpha")

    def runner(cmd, cwd):
        return '[{"title": "no number here"}, {"number": 2, "title": "ok"}]'

    src = TrackerSource("tracker", {"mrconfig": str(cfg), "command": ["gh"]}, runner=runner)
    res = src.read(Query(text="alpha#2", kinds=frozenset({KIND_NODES})))
    assert [n.id for n in res.nodes] == ["alpha#2"]  # the numberless issue is skipped, not `alpha#None`


def test_produces_is_nodes_only():
    assert TrackerSource("tracker").produces == frozenset({KIND_NODES})


# --- iris#36: the fan-out is scoped to the repos the query names ---


def test_scopes_fanout_to_cited_repos_only(tmp_path):
    # three repos in the registry, but the query names only one → one forge spawn, in that repo
    cfg, _ = _mrconfig(tmp_path, "alpha", "beta", "gamma")
    calls: list[str] = []

    def runner(cmd, cwd):
        calls.append(Path(cwd).name)
        return '[{"number": 1, "title": "only alpha"}]'

    src = TrackerSource("tracker", {"mrconfig": str(cfg), "command": ["gh"]}, runner=runner)
    res = src.read(Query(text="mexer em alpha#29", kinds=frozenset({KIND_NODES})))

    assert res.ok
    assert calls == ["alpha"]  # beta/gamma never spawned
    assert [n.id for n in res.nodes] == ["alpha#1"]


def test_no_repo_cited_spawns_nothing(tmp_path):
    # a query naming no `<repo>#<n>` (a bare context, or repos/ground carrying no task text) does NOT
    # read the registry and spawns no forge subprocess — the ergonomic default (iris#36)
    cfg, _ = _mrconfig(tmp_path, "alpha", "beta")
    calls: list[str] = []

    def runner(cmd, cwd):
        calls.append(Path(cwd).name)
        return "[]"

    src = TrackerSource("tracker", {"mrconfig": str(cfg), "command": ["gh"]}, runner=runner)
    res = src.read(Query(text="clean up /storage; nothing repo-shaped here", kinds=frozenset({KIND_NODES})))

    assert res.ok
    assert res.nodes == [] and res.relations == []
    assert calls == []  # no fan-out at all


def test_empty_query_text_spawns_nothing(tmp_path):
    # `repos`/`ground` pass no text → zero targets → no fan-out (this is what makes enabling the
    # tracker in an active config cost-free for those reads)
    cfg, _ = _mrconfig(tmp_path, "alpha", "beta")
    calls: list[str] = []

    def runner(cmd, cwd):
        calls.append(Path(cwd).name)
        return "[]"

    src = TrackerSource("tracker", {"mrconfig": str(cfg), "command": ["gh"]}, runner=runner)
    res = src.read(Query(kinds=frozenset({KIND_NODES})))

    assert res.ok and calls == []


def test_cited_repo_absent_from_registry_is_silently_empty(tmp_path):
    # a query naming a repo not in the mrconfig registry has nothing to query → empty, no spawn,
    # no failure (the tracker only knows registry repos; a non-registry slug is simply out of reach)
    cfg, _ = _mrconfig(tmp_path, "alpha")
    calls: list[str] = []

    def runner(cmd, cwd):
        calls.append(Path(cwd).name)
        return "[]"

    src = TrackerSource("tracker", {"mrconfig": str(cfg), "command": ["gh"]}, runner=runner)
    res = src.read(Query(text="work on stranger#5", kinds=frozenset({KIND_NODES})))

    assert res.ok and res.nodes == [] and calls == []
