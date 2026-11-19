"""SP-T6 [v2] gate (Spec spec-repo-issues-federation v2): the repo join identity is the forge name.

A registry checkout whose directory differs from its forge repo name is keyed by the forge name in the
constellation node, the tracker's issues and the chain/inbound resolution; an entry with no forge slug falls
back to its basename; a name two entries would take is ambiguous — taken by neither, reported, never guessed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from typer.testing import CliRunner

from iris import cli
from iris.core.source import KIND_CHAIN, KIND_NODES, Query
from iris.sources._repos import identity_map, repo_entries
from iris.sources.constellation import ConstellationSource
from iris.sources.tracker import TrackerSource


def _checkout(root: Path, dirname: str, origin: str | None) -> Path:
    """A checkout directory whose `.git/config` names `origin` (or no remote at all)."""
    repo = root / dirname
    (repo / ".git").mkdir(parents=True)
    body = f'[remote "origin"]\n\turl = {origin}\n' if origin else "[core]\n\tbare = false\n"
    (repo / ".git" / "config").write_text(body, encoding="utf-8")
    return repo


def _mrconfig(root: Path, sections: list[tuple[Path, str]]) -> Path:
    mrconfig = root / ".mrconfig"
    mrconfig.write_text(
        "".join(f"[{path}]\n" + (f"checkout = {checkout}\n" if checkout else "") for path, checkout in sections),
        encoding="utf-8",
    )
    return mrconfig


# --- the derivation -----------------------------------------------------------------------------------


def test_registry_checkout_named_a_with_origin_b_is_keyed_b(tmp_path: Path) -> None:
    repo = _checkout(tmp_path, "a", "git@github.com:owner/b.git")
    ids = identity_map(repo_entries(_mrconfig(tmp_path, [(repo, "")])))
    assert ids.by_path[repo] == "b"
    assert ids.slugs[repo] == "github.com/owner/b"
    assert ids.ambiguous == frozenset()


def test_absent_checkout_takes_its_forge_name_from_the_checkout_command(tmp_path: Path) -> None:
    absent = tmp_path / "gone"
    mrconfig = _mrconfig(tmp_path, [(absent, "git clone 'git@gitlab.example.org:group/sub/real-name.git' 'gone'")])
    assert identity_map(repo_entries(mrconfig)).by_path[absent] == "real-name"


def test_entry_without_forge_slug_falls_back_to_its_basename(tmp_path: Path) -> None:
    repo = _checkout(tmp_path, "plain", None)
    assert identity_map(repo_entries(_mrconfig(tmp_path, [(repo, "")]))).by_path[repo] == "plain"


def test_two_entries_with_one_forge_name_are_ambiguous_and_keyed_by_path(tmp_path: Path) -> None:
    one = _checkout(tmp_path, "x1", "git@github.com:org1/foo.git")
    two = _checkout(tmp_path, "x2", "https://gitlab.example.org/org2/foo.git")
    ids = identity_map(repo_entries(_mrconfig(tmp_path, [(one, ""), (two, "")])))
    assert ids.ambiguous == frozenset({"foo"})
    assert ids.by_path == {one: str(one), two: str(two)}


def test_fallback_basename_against_another_forge_name_is_ambiguous(tmp_path: Path) -> None:
    named = _checkout(tmp_path, "elsewhere", "git@github.com:org/foo.git")
    local = _checkout(tmp_path, "foo", None)
    ids = identity_map(repo_entries(_mrconfig(tmp_path, [(named, ""), (local, "")])))
    assert ids.ambiguous == frozenset({"foo"})
    assert "foo" not in ids.by_path.values()


# --- constellation -------------------------------------------------------------------------------------


def test_constellation_repo_node_id_is_the_forge_name(tmp_path: Path) -> None:
    repo = _checkout(tmp_path, "a", "git@github.com:owner/b.git")
    mrconfig = _mrconfig(tmp_path, [(repo, "")])
    result = ConstellationSource("constellation", {"mrconfig": str(mrconfig)}).read(Query())
    assert [n.id for n in result.nodes if n.kind == "repo"] == ["b"]


def test_constellation_notes_an_ambiguous_name(tmp_path: Path) -> None:
    one = _checkout(tmp_path, "x1", "git@github.com:org1/foo.git")
    two = _checkout(tmp_path, "x2", "git@github.com:org2/foo.git")
    mrconfig = _mrconfig(tmp_path, [(one, ""), (two, "")])
    result = ConstellationSource("constellation", {"mrconfig": str(mrconfig)}).read(Query())
    assert "ambiguous identity (two or more registry entries): foo" in result.note
    assert {n.id for n in result.nodes if n.kind == "repo"} == {str(one), str(two)}


# --- tracker -------------------------------------------------------------------------------------------


def test_tracker_keys_issues_by_forge_name_and_pins_the_cli_to_the_slug(tmp_path: Path) -> None:
    repo = _checkout(tmp_path, "a", "git@github.com:owner/b.git")
    mrconfig = _mrconfig(tmp_path, [(repo, "")])
    calls: list[tuple[list[str], Path]] = []

    def runner(cmd: list[str], cwd: Path) -> str:
        calls.append((cmd, cwd))
        return json.dumps([{"number": 7, "title": "T"}])

    source = TrackerSource("tracker", {"mrconfig": str(mrconfig), "command": ["gh", "-R", "{slug}"]}, runner=runner)
    result = source.read(Query(text="see b#7", kinds=frozenset({KIND_NODES})))
    assert calls == [(["gh", "-R", "github.com/owner/b"], repo)]
    assert [n.id for n in result.nodes] == ["b#7"]
    assert [(r.from_, r.to) for r in result.relations] == [("b", "b#7")]


def test_tracker_chain_resolves_the_forge_name_with_slug_and_number(tmp_path: Path) -> None:
    repo = _checkout(tmp_path, "a", "git@github.com:owner/b.git")
    mrconfig = _mrconfig(tmp_path, [(repo, "")])
    calls: list[list[str]] = []

    def runner(cmd: list[str], cwd: Path) -> str:
        calls.append(cmd)
        return json.dumps({"number": 5, "title": "T", "state": "OPEN"})

    view = ["glab", "issue", "view", "{number}", "-R", "https://{slug}"]
    source = TrackerSource("tracker", {"mrconfig": str(mrconfig), "view": view}, runner=runner)
    result = source.read(Query(text="b#5", kinds=frozenset({KIND_CHAIN})))
    assert calls == [["glab", "issue", "view", "5", "-R", "https://github.com/owner/b"]]
    assert [(n.id, n.roles) for n in result.nodes] == [("b#5", ["open"])]
    # the checkout's directory name is not an identity
    assert TrackerSource("tracker", {"mrconfig": str(mrconfig), "view": view}, runner=runner).read(
        Query(text="a#5", kinds=frozenset({KIND_CHAIN}))
    ).nodes == []


def test_tracker_chain_ref_to_an_ambiguous_name_resolves_nothing_and_says_why(tmp_path: Path) -> None:
    one = _checkout(tmp_path, "x1", "git@github.com:org1/foo.git")
    two = _checkout(tmp_path, "x2", "git@github.com:org2/foo.git")
    mrconfig = _mrconfig(tmp_path, [(one, ""), (two, "")])
    source = TrackerSource(
        "tracker", {"mrconfig": str(mrconfig), "view": ["gh", "{number}"]}, runner=lambda c, w: "{}"
    )
    result = source.read(Query(text="foo#3", kinds=frozenset({KIND_CHAIN})))
    assert result.nodes == []
    assert "ambiguous identity (two or more registry entries): foo" in result.note


# --- inbound, end to end: the 2026-11-19 split is closed -----------------------------------------------


def _inbound_config(tmp_path: Path) -> Path:
    repo = _checkout(tmp_path, "a", "git@github.com:owner/b.git")
    mrconfig = _mrconfig(tmp_path, [(repo, "")])
    view = (
        "import json,sys; print(json.dumps({'number': int(sys.argv[1]), 'title': 'the item', 'state': 'OPEN'}))"
    )
    # the store cites the repo by its forge name — it answers for `b#5` and for nothing else
    store = (
        "import json,sys; print(json.dumps([{'source': 'journal/x.md#blk', 'type': 'refs'}] "
        "if sys.argv[1] == 'b#5' else []))"
    )
    config = tmp_path / "sources.toml"
    config.write_text(
        f'[sources.constellation]\ntype = "constellation"\nmrconfig = "{mrconfig}"\n\n'
        f'[sources.tracker]\ntype = "tracker"\nmrconfig = "{mrconfig}"\n'
        f'view = ["{sys.executable}", "-c", "{view}", "{{number}}"]\n'
        f'[sources.tracker.map]\nstate = "state"\n\n'
        f'[sources.notes]\ntype = "cli-json"\ncommand = ["true"]\n'
        f'[sources.notes.inbound]\ncommand = ["{sys.executable}", "-c", "{store}", "{{key}}"]\nitems = ""\n'
        f'[sources.notes.inbound.map]\nlocator = "source"\ntype = "type"\n',
        encoding="utf-8",
    )
    return config


def test_inbound_by_forge_name_resolves_the_item_and_returns_the_store_citations(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(_inbound_config(tmp_path)))
    result = CliRunner().invoke(cli.app, ["inbound", "b#5"])
    assert result.exit_code == 0, result.output
    assert "b#5  [open]  the item" in result.stdout
    assert "journal/x.md#blk" in result.stdout
