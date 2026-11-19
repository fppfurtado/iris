"""spec-repo-issues-federation v3 SP-T8 (iris#81) — one tracker instance serves several forges by host
(`forges."<host>"`), a repo no CLI serves is UNSERVED (never skipped silently), and the issue state read by
`view` maps through `states` to the canonical open/closed."""

from __future__ import annotations

import json
from pathlib import Path

from iris.core.source import KIND_CHAIN, KIND_NODES, Query
from iris.sources.tracker import TrackerSource

_GH_HOST = "gh.example"
_GL_HOST = "gl.example"


def _checkout(root: Path, name: str, origin: str | None) -> Path:
    repo = root / name
    (repo / ".git").mkdir(parents=True)
    body = f'[remote "origin"]\n\turl = {origin}\n' if origin else "[core]\n\tbare = false\n"
    (repo / ".git" / "config").write_text(body, encoding="utf-8")
    return repo


def _registry(tmp_path: Path) -> Path:
    repos = [
        _checkout(tmp_path, "hub", f"git@{_GH_HOST}:owner/hub.git"),
        _checkout(tmp_path, "lab", f"git@{_GL_HOST}:group/lab.git"),
        _checkout(tmp_path, "solo", None),
    ]
    cfg = tmp_path / ".mrconfig"
    cfg.write_text("\n".join(f"[{r}]" for r in repos) + "\n", encoding="utf-8")
    return cfg


def _opts(cfg: Path, **extra) -> dict:
    opts = {
        "mrconfig": str(cfg),
        "command": ["gh", "issue", "list"],
        "view": ["gh", "issue", "view", "{number}"],
        "map": {"number": "number", "title": "title", "state": "state"},
        "forges": {
            _GL_HOST: {
                "command": ["glab", "issue", "list", "-R", "https://{slug}"],
                "view": ["glab", "issue", "view", "{number}", "-R", "https://{slug}"],
                "map": {"number": "iid"},
                "states": {"opened": "open"},
            }
        },
    }
    opts.update(extra)
    return opts


def _runner(calls: list | None = None, gl_state: str = "opened"):
    def run(cmd, cwd):
        if calls is not None:
            calls.append((cmd[0], Path(cwd).name, cmd))
        if cmd[0] == "glab":
            if cmd[2] == "list":
                return json.dumps([{"iid": 3, "title": "lab issue"}])
            return json.dumps({"iid": int(cmd[3]), "title": "lab issue", "state": gl_state})
        if Path(cwd).name == "lab":
            raise RuntimeError("gh: not a GitHub repo")
        if cmd[2] == "list":
            return json.dumps([{"number": 1, "title": "hub issue"}])
        return json.dumps({"number": int(cmd[3]), "title": "hub issue", "state": "OPEN"})

    return run


def test_mixed_registry_context_reads_both_forges_without_degrading(tmp_path):
    calls: list = []
    src = TrackerSource("tracker", _opts(_registry(tmp_path)), runner=_runner(calls))
    res = src.read(Query(text="hub#1 and lab#3", kinds=frozenset({KIND_NODES})))
    assert res.ok, res.note
    assert sorted(n.id for n in res.nodes) == ["hub#1", "lab#3"]
    assert "unreadable" not in res.note
    by_repo = {repo: (tool, cmd) for tool, repo, cmd in calls}
    assert by_repo["hub"][0] == "gh"
    assert by_repo["lab"] == ("glab", ["glab", "issue", "list", "-R", f"https://{_GL_HOST}/group/lab"])


def test_mixed_registry_chain_maps_glab_opened_to_open(tmp_path):
    src = TrackerSource("tracker", _opts(_registry(tmp_path)), runner=_runner())
    res = src.read(Query(text="hub#1 lab#3", kinds=frozenset({KIND_CHAIN})))
    assert res.ok, res.note
    roles = {n.id: n.roles for n in res.nodes}
    assert roles == {"hub#1": ["open"], "lab#3": ["open"]}


def test_closed_maps_through_identity_beneath_states(tmp_path):
    src = TrackerSource("tracker", _opts(_registry(tmp_path)), runner=_runner(gl_state="closed"))
    res = src.read(Query(text="lab#3", kinds=frozenset({KIND_CHAIN})))
    assert [n.roles for n in res.nodes] == [["closed"]]


def test_states_keys_and_values_are_case_insensitive(tmp_path):
    opts = _opts(_registry(tmp_path))
    opts["forges"][_GL_HOST]["states"] = {"Opened": "Open"}
    src = TrackerSource("tracker", opts, runner=_runner(gl_state="OPENED"))
    res = src.read(Query(text="lab#3", kinds=frozenset({KIND_CHAIN})))
    assert res.ok, res.note
    assert [n.roles for n in res.nodes] == [["open"]]


def test_unmapped_state_has_no_role_and_a_note_naming_it(tmp_path):
    src = TrackerSource("tracker", _opts(_registry(tmp_path)), runner=_runner(gl_state="locked"))
    res = src.read(Query(text="lab#3", kinds=frozenset({KIND_CHAIN})))
    assert [n.roles for n in res.nodes] == [[]]
    assert "state 'locked' not mapped" in res.note


def test_missing_state_has_no_role_and_no_unmapped_note(tmp_path):
    for missing in ("", None, False):
        src = TrackerSource("tracker", _opts(_registry(tmp_path / str(missing))), runner=_runner(gl_state=missing))
        res = src.read(Query(text="lab#3", kinds=frozenset({KIND_CHAIN})))
        assert [n.roles for n in res.nodes] == [[]]
        assert "not mapped" not in res.note


def test_unserved_repo_is_unreadable_with_a_host_note_never_silent(tmp_path):
    opts = _opts(_registry(tmp_path), command=[], view=[])  # only the gitlab host is served
    src = TrackerSource("tracker", opts, runner=_runner())
    ctx = src.read(Query(text="hub#1 lab#3 solo#2", kinds=frozenset({KIND_NODES})))
    assert not ctx.ok
    assert f"1 repo(s) unserved ({_GH_HOST}): no `command`" in ctx.note
    assert "1 repo(s) unserved (no forge host): no `command`" in ctx.note
    assert [n.id for n in ctx.nodes] == ["lab#3"]
    chain = src.read(Query(text="hub#1 lab#3", kinds=frozenset({KIND_CHAIN})))
    assert not chain.ok
    assert f"chain: 1 ref(s) unserved ({_GH_HOST}): no `view` command" in chain.note


def test_local_slug_uses_the_top_level(tmp_path):
    calls: list = []
    src = TrackerSource("tracker", _opts(_registry(tmp_path)), runner=_runner(calls))
    src.read(Query(text="solo#2", kinds=frozenset({KIND_NODES})))
    assert [tool for tool, repo, _ in calls] == ["gh"]


def test_config_errors_degrade_every_read_naming_a_ref(tmp_path):
    cfg = _registry(tmp_path)
    opts = _opts(cfg)
    opts["forges"]["GL.EXAMPLE"] = {"command": ["other"]}  # duplicate after lowercasing → later ignored
    opts["forges"]["nested"] = {"example": {"command": ["x"]}}  # an unquoted dotted key TOML nested
    opts["states"] = {"opened": "done"}  # not an issue state
    src = TrackerSource("tracker", opts, runner=_runner())
    res = src.read(Query(text="hub#1 lab#3", kinds=frozenset({KIND_NODES})))
    assert not res.ok
    assert "forges.GL.EXAMPLE duplicates host" in res.note
    assert "forges.nested carries no command or view" in res.note
    assert "states.opened" in res.note
    assert sorted(n.id for n in res.nodes) == ["hub#1", "lab#3"]  # the first gitlab entry still serves
    chain = src.read(Query(text="lab#3", kinds=frozenset({KIND_CHAIN})))
    assert not chain.ok and "duplicates host" in chain.note
    # a read naming no `<repo>#<n>` ref spawns nothing and stays ok
    assert src.read(Query(text="^anchor only", kinds=frozenset({KIND_CHAIN}))).ok
    assert src.read(Query(text="no refs", kinds=frozenset({KIND_NODES}))).ok


def test_a_forges_entry_overrides_per_key_and_inherits_the_rest(tmp_path):
    calls: list = []
    opts = _opts(_registry(tmp_path))
    opts["forges"][_GL_HOST] = {"view": ["glab", "issue", "view", "{number}"], "map": {"number": "iid"}}
    src = TrackerSource("tracker", opts, runner=_runner(calls))
    src.read(Query(text="lab#3", kinds=frozenset({KIND_NODES})))  # context: inherits the top-level gh command
    assert calls[-1][0] == "gh"
    res = src.read(Query(text="lab#3", kinds=frozenset({KIND_CHAIN})))
    assert calls[-1][0] == "glab"
    # inherited top-level map keys (title/state) still apply beside the entry's number = iid
    assert [n.title for n in res.nodes] == ["lab issue"]


# --- end to end: `iris chain` over a mixed registry, through a real TOML config (quoted host key) ---


def test_cli_chain_over_a_mixed_registry(tmp_path, monkeypatch):
    import sys

    from typer.testing import CliRunner

    import iris.cli as cli

    cfg = _registry(tmp_path)
    gh = "import json,sys; print(json.dumps({'number': int(sys.argv[1]), 'title': 'hub', 'state': 'CLOSED'}))"
    gl = "import json,sys; print(json.dumps({'iid': int(sys.argv[1]), 'title': 'lab', 'state': 'opened'}))"
    config = tmp_path / "sources.toml"
    config.write_text(
        f'[sources.tracker]\ntype = "tracker"\nmrconfig = "{cfg}"\n'
        f'view = ["{sys.executable}", "-c", "{gh}", "{{number}}"]\n'
        f'[sources.tracker.map]\nstate = "state"\n'
        f'[sources.tracker.forges."{_GL_HOST}"]\n'
        f'view = ["{sys.executable}", "-c", "{gl}", "{{number}}"]\n'
        f'map = {{ number = "iid" }}\nstates = {{ opened = "open" }}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("IRIS_CONFIG", str(config))
    result = CliRunner().invoke(cli.app, ["chain", "hub#1 gated on lab#3"])
    assert result.exit_code == 0, result.output
    out = result.stdout
    assert "## candidate blockers" in out and "lab#3" in out.split("## resolved")[0]
    assert "hub#1  [closed]" in out
    assert "degraded" not in result.output and "unserved" not in result.output


# --- review fixes R2/R3 (iris#81) ---


def test_forges_key_matches_case_and_port_insensitively(tmp_path):
    calls: list = []
    opts = _opts(_registry(tmp_path))
    opts["forges"] = {"GL.Example:2222": opts["forges"][_GL_HOST]}
    src = TrackerSource("tracker", opts, runner=_runner(calls))
    res = src.read(Query(text="lab#3", kinds=frozenset({KIND_NODES})))
    assert res.ok, res.note
    assert calls[-1][0] == "glab"


def test_a_forges_entry_overrides_items(tmp_path):
    opts = _opts(_registry(tmp_path))
    opts["forges"][_GL_HOST]["items"] = "data"

    def run(cmd, cwd):
        return json.dumps({"data": [{"iid": 9, "title": "wrapped"}]})

    res = TrackerSource("tracker", opts, runner=run).read(Query(text="lab#9", kinds=frozenset({KIND_NODES})))
    assert [n.id for n in res.nodes] == ["lab#9"]


def test_malformed_forges_values_are_config_errors_not_crashes(tmp_path):
    opts = _opts(_registry(tmp_path))
    opts["forges"][_GL_HOST]["map"] = "iid"  # not a table
    src = TrackerSource("tracker", opts, runner=_runner())
    res = src.read(Query(text="hub#1 lab#3", kinds=frozenset({KIND_NODES})))
    assert not res.ok
    assert f"forges.{_GL_HOST} has a malformed map" in res.note
    assert [n.id for n in res.nodes] == ["hub#1"]  # gh still serves its host; lab falls to gh and fails loudly
