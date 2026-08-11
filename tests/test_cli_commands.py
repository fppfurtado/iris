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
