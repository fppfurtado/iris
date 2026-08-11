"""SP-T7 gate: `iris repos --tag pro-bono` returns the matching repos + state in one
call; and federation isolates a failing source."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from iris.cli import app
from iris.config import Config, SourceSpec
from iris.core.federation import federate
from iris.core.model import Node
from iris.core.registry import Registry
from iris.core.source import Query, SourceResult

runner = CliRunner()


class _Boom:
    name = "boom"

    def read(self, query: Query) -> SourceResult:
        raise RuntimeError("nope")


class _Good:
    name = "good"

    def read(self, query: Query) -> SourceResult:
        return SourceResult(nodes=[Node(id="n", kind="repo", title="n")])


def test_federate_isolates_a_failing_source() -> None:
    reg = Registry()
    reg.register("boom", lambda name, opts: _Boom())
    reg.register("good", lambda name, opts: _Good())
    config = Config(sources=[SourceSpec("boom", {}), SourceSpec("good", {})])

    result = federate(config, Query(), reg)

    assert [n.id for n in result.nodes] == ["n"]  # the good source survives
    assert any("boom" in note and "failed" in note for note in result.notes)


def _fixture_config(tmp_path: Path) -> Path:
    tagged = tmp_path / "relatorios-h3"
    tagged.mkdir()
    (tagged / "catalog-info.yaml").write_text(
        "metadata:\n  tags: [pro-bono]\nspec:\n  type: service\n", encoding="utf-8"
    )
    other = tmp_path / "meta-system"
    other.mkdir()
    (other / "catalog-info.yaml").write_text(
        "metadata:\n  tags: [meta]\nspec:\n  type: library\n", encoding="utf-8"
    )
    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(f"[{tagged}]\ncheckout = x\n\n[{other}]\ncheckout = y\n", encoding="utf-8")
    config = tmp_path / "sources.toml"
    config.write_text(f'[sources.constellation]\nmrconfig = "{mrconfig}"\n', encoding="utf-8")
    return config


def test_repos_tag_returns_matching_repos_in_one_call(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(_fixture_config(tmp_path)))
    result = runner.invoke(app, ["repos", "--tag", "pro-bono"])
    assert result.exit_code == 0
    assert "relatorios-h3" in result.output  # the pro-bono repo, with state
    assert "pro-bono" in result.output
    assert "meta-system" not in result.output  # non-matching repo filtered out
