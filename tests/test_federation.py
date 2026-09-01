"""SP-T7 gate: `iris repos --tag pro-bono` returns the matching repos + state in one
call; and federation isolates a failing source. Also: federation is kind-aware — a
query that declares the kinds it consumes skips a source that produces none of them
(iris#7)."""

from __future__ import annotations

from typer.testing import CliRunner

from iris.cli import app
from iris.config import Config, SourceSpec
from iris.core.federation import federate
from iris.core.model import GroundHit, Node
from iris.core.registry import Registry
from iris.core.source import KIND_HITS, KIND_NODES, Query, SourceResult

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


def test_federation_skips_a_source_whose_kinds_are_not_wanted() -> None:
    calls: list[str] = []

    class _NodesOnly:
        name = "nodes-only"
        produces = frozenset({KIND_NODES})

        def read(self, query: Query) -> SourceResult:
            calls.append("nodes")
            return SourceResult(nodes=[Node(id="n", kind="repo", title="n")])

    class _HitsOnly:
        name = "hits-only"
        produces = frozenset({KIND_HITS})

        def read(self, query: Query) -> SourceResult:
            calls.append("hits")
            return SourceResult(hits=[GroundHit(ref="r", excerpt="e")])

    reg = Registry()
    reg.register("nodes-only", lambda name, opts: _NodesOnly())
    reg.register("hits-only", lambda name, opts: _HitsOnly())
    config = Config(sources=[SourceSpec("nodes-only", {}), SourceSpec("hits-only", {})])

    # A query that consumes only hits must NOT invoke the nodes-only source at all.
    result = federate(config, Query(kinds=frozenset({KIND_HITS})), reg)

    assert calls == ["hits"]  # the nodes-only source was skipped, not just filtered
    assert [h.ref for h in result.hits] == ["r"]
    assert result.nodes == []


def test_federation_reads_a_source_that_declares_no_kinds() -> None:
    # A source without a `produces` attribute is "undeclared" → always read, even
    # under a narrow kinds query (backward compatibility with pre-#7 sources).
    class _Undeclared:
        name = "undeclared"

        def read(self, query: Query) -> SourceResult:
            return SourceResult(nodes=[Node(id="u", kind="repo", title="u")])

    reg = Registry()
    reg.register("undeclared", lambda name, opts: _Undeclared())
    config = Config(sources=[SourceSpec("undeclared", {})])

    result = federate(config, Query(kinds=frozenset({KIND_HITS})), reg)

    assert [n.id for n in result.nodes] == ["u"]  # read despite the hits-only query


def test_repos_tag_returns_matching_repos_in_one_call(constellation_config, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(constellation_config))
    result = runner.invoke(app, ["repos", "--tag", "pro-bono"])
    assert result.exit_code == 0
    assert "relatorios-h3" in result.output  # the pro-bono repo, with state
    assert "pro-bono" in result.output
    assert "meta-system" not in result.output  # non-matching repo filtered out
