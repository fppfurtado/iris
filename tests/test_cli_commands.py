"""Review finding #4: the `ground` and `context` CLI commands run and render composed
output (SP-T7 / PR6). Uses a real cli-json subprocess (a python3 one-liner emitting
canned JSON) so the generic source path is exercised end-to-end, plus constellation."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from iris.cli import app

runner = CliRunner()

_FAKE_JSON = (
    "import json; print(json.dumps({'items':[{'ref':'r1','excerpt':'E',"
    "'trust':{'status':'ok','age_days':1}}]}))"
)


def _config(tmp_path: Path) -> Path:
    repo = tmp_path / "meta-system"
    repo.mkdir()
    (repo / "catalog-info.yaml").write_text(
        "metadata:\n  tags: [meta]\nspec:\n  type: library\n", encoding="utf-8"
    )
    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(f"[{repo}]\ncheckout = x\n", encoding="utf-8")
    cfg = tmp_path / "sources.toml"
    cfg.write_text(
        f'[sources.constellation]\ntype = "constellation"\nmrconfig = "{mrconfig}"\n\n'
        f'[sources.fake]\ntype = "cli-json"\ncommand = ["python3", "-c", "{_FAKE_JSON}"]\n'
        'items = "items"\n[sources.fake.map]\nref = "ref"\nexcerpt = "excerpt"\n',
        encoding="utf-8",
    )
    return cfg


def test_ground_renders_hits(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(_config(tmp_path)))
    result = runner.invoke(app, ["ground", "anything"])
    assert result.exit_code == 0
    assert "r1" in result.output
    assert "E" in result.output


def test_context_composes_repos_and_grounding(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(_config(tmp_path)))
    result = runner.invoke(app, ["context", "some task"])
    assert result.exit_code == 0
    assert "## repos" in result.output
    assert "meta-system" in result.output
    assert "## grounding" in result.output
    assert "r1" in result.output


_FAKE_ISSUES = "import json; print(json.dumps([{'number': 5, 'title': 'ISSUE-TITLE'}]))"


def _config_with_tracker(tmp_path: Path) -> Path:
    repo = tmp_path / "meta-system"
    repo.mkdir()
    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(f"[{repo}]\ncheckout = x\n", encoding="utf-8")
    cfg = tmp_path / "sources.toml"
    cfg.write_text(
        f'[sources.constellation]\ntype = "constellation"\nmrconfig = "{mrconfig}"\n\n'
        f'[sources.tracker]\ntype = "tracker"\nmrconfig = "{mrconfig}"\n'
        f'command = ["python3", "-c", "{_FAKE_ISSUES}"]\n',
        encoding="utf-8",
    )
    return cfg


def test_context_joins_open_issues_under_their_repo(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(_config_with_tracker(tmp_path)))
    # the task names the repo (iris#36: the tracker scopes its fan-out to the repos the query cites)
    result = runner.invoke(app, ["context", "some task on meta-system#5"])
    assert result.exit_code == 0
    assert "## repos" in result.output
    assert "meta-system" in result.output
    # the issue is rendered under its repo (the cross-source join), not as a bare list
    assert "meta-system#5" in result.output
    assert "ISSUE-TITLE" in result.output


def test_context_surfaces_unmatched_issue(tmp_path, monkeypatch) -> None:
    # constellation sees `alpha`; the tracker (a DIFFERENT mrconfig) sees `ghost` — so ghost's issue
    # matches no repo node and must surface under `## unmatched issues` (the F6 identity-miss), not vanish.
    alpha = tmp_path / "alpha"
    alpha.mkdir()
    con_mr = tmp_path / "con.mrconfig"
    con_mr.write_text(f"[{alpha}]\ncheckout = x\n", encoding="utf-8")
    ghost = tmp_path / "ghost"
    ghost.mkdir()
    trk_mr = tmp_path / "trk.mrconfig"
    trk_mr.write_text(f"[{ghost}]\ncheckout = x\n", encoding="utf-8")
    cfg = tmp_path / "sources.toml"
    cfg.write_text(
        f'[sources.constellation]\ntype = "constellation"\nmrconfig = "{con_mr}"\n\n'
        f'[sources.tracker]\ntype = "tracker"\nmrconfig = "{trk_mr}"\n'
        f'command = ["python3", "-c", "{_FAKE_ISSUES}"]\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("IRIS_CONFIG", str(cfg))
    # the task cites ghost, so the tracker spawns there (iris#36); ghost matches no repo node → unmatched
    result = runner.invoke(app, ["context", "look at ghost#5"])
    assert result.exit_code == 0
    assert "## unmatched issues" in result.output
    assert "ghost#5" in result.output


_FAKE_TASKS = (
    "import json; print(json.dumps([{'id':'aa1','text':'do meta-system#9 now'},"
    "{'id':'bb2','text':'unrelated storage cleanup'}]))"
)


def _config_with_tasks(tmp_path: Path) -> Path:
    repo = tmp_path / "meta-system"
    repo.mkdir()
    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(f"[{repo}]\ncheckout = x\n", encoding="utf-8")
    cfg = tmp_path / "sources.toml"
    cfg.write_text(
        f'[sources.constellation]\ntype = "constellation"\nmrconfig = "{mrconfig}"\n\n'
        f'[sources.gtd]\ntype = "tasks"\ncommand = ["python3", "-c", "{_FAKE_TASKS}"]\n',
        encoding="utf-8",
    )
    return cfg


def test_context_joins_referencing_tasks_under_their_repo(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(_config_with_tasks(tmp_path)))
    result = runner.invoke(app, ["context", "some task"])
    assert result.exit_code == 0
    # the task that names meta-system#9 is rendered under meta-system (the cross-source join)
    assert "task ^aa1" in result.output
    assert "do meta-system#9 now" in result.output
    # the task naming no repo is outside the join — not rendered
    assert "bb2" not in result.output
