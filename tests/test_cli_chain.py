"""F6-T5 — the `iris chain` surface (CLI) + MCP parity: the blocker-view IA.

The fetch is covered in the source tests (F6-T2/T3); here we assert the PRESENTATION — candidate
blockers first, a distinct UNKNOWN section, and the failure-mode guard (never 'clear' while unknown)."""

from __future__ import annotations

from types import SimpleNamespace

import iris.cli as cli
import iris.mcp_adapter as mcp_adapter
from iris.core.federation import FederationResult
from iris.core.model import Node
from typer.testing import CliRunner

runner = CliRunner()

_FAKE_CONFIG = SimpleNamespace(sources=[])


def _canned(monkeypatch, module, nodes, notes=None):
    def fake_federate(config, query, *a, **k):
        assert "chain" in query.kinds  # the surface asks for the chain kind
        return FederationResult(nodes=nodes, notes=notes or [])

    monkeypatch.setattr(module, "federate", fake_federate)
    monkeypatch.setattr(module, "_load_config" if module is cli else "active_config", lambda *a, **k: _FAKE_CONFIG)


_CHAIN_NODES = [
    Node(id="iris#6", kind="issue", title="min scrub", roles=["closed"]),
    Node(id="iris#5", kind="issue", title="public flip", roles=["open"]),
    Node(id="dogfd1", kind="task", title="review dogfood gate:dogfood", roles=["open"]),
]


def test_cli_chain_renders_blockers_first_and_nonblockers(tmp_path, monkeypatch):
    _canned(monkeypatch, cli, _CHAIN_NODES)
    result = runner.invoke(cli.app, ["chain", "flip gated on iris#6, ^dogfd1 and iris#5"])
    assert result.exit_code == 0
    out = result.output
    assert "## candidate blockers" in out
    assert "^dogfd1" in out and "iris#5" in out  # OPEN refs are candidate blockers
    assert "[gate]" in out  # the gate marker is emphasized
    # iris#6 CLOSED -> the resolved-not-blocking section, not a blocker
    assert "## resolved (not blocking)" in out
    assert out.index("## candidate blockers") < out.index("## resolved")  # blockers surfaced FIRST


def test_cli_chain_unknown_ref_is_distinct_and_not_clear(monkeypatch):
    _canned(
        monkeypatch,
        cli,
        [Node(id="iris#6", kind="issue", title="done", roles=["closed"])],
        notes=["tracker: chain: 1 ref(s) unreadable"],
    )
    result = runner.invoke(cli.app, ["chain", "iris#6 and iris#99"])
    assert result.exit_code == 0
    assert "## unknown" in result.output  # the unresolved ref gets its own section
    assert "iris#99" in result.output
    # failure-mode guard: with an unknown ref present, never claim no-open-blockers
    assert "no open blockers" not in result.output


def test_cli_chain_all_closed_no_unknown_says_no_blockers(monkeypatch):
    _canned(monkeypatch, cli, [Node(id="iris#6", kind="issue", title="done", roles=["closed"])])
    result = runner.invoke(cli.app, ["chain", "iris#6"])
    assert result.exit_code == 0
    assert "no open blockers among the resolved refs" in result.output


def test_mcp_chain_parity_keeps_unknown_distinct(monkeypatch):
    _canned(monkeypatch, mcp_adapter, _CHAIN_NODES + [], notes=[])
    # add an unresolvable ref via item text (iris#99 has no node)
    out = mcp_adapter.chain.fn("flip iris#6 ^dogfd1 iris#5 iris#99")
    assert {n["id"] for n in out["blocker_candidates"]} == {"iris#5", "dogfd1"}
    assert [n["id"] for n in out["resolved_non_blocking"]] == ["iris#6"]
    assert out["unknown_unresolved"] == ["iris#99"]  # distinct key, parity with CLI
    assert any(b["gate_marked"] for b in out["blocker_candidates"])
