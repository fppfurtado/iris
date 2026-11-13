"""SP-T8 gate: an MCP client connects, lists read-only tools, and gets the SAME
result as the CLI."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastmcp import Client
from typer.testing import CliRunner

from iris.cli import app
from iris.mcp_adapter import mcp


async def _connect_and_call(tag: str) -> tuple[set[str], list[dict]]:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        result = await client.call_tool("repos", {"tag": tag})
    return {t.name for t in tools}, result.structured_content["result"]


async def _call_context(task: str) -> dict:
    async with Client(mcp) as client:
        result = await client.call_tool("context", {"task": task})
    sc = result.structured_content
    return sc.get("result", sc)


def test_mcp_client_lists_read_only_tools_and_matches_cli(constellation_config, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(constellation_config))

    names, data = asyncio.run(_connect_and_call("pro-bono"))

    # an MCP client connected and saw the read-only tools
    assert {"ground", "repos"} <= names

    # the tool returns the pro-bono repo — SAME as the CLI for the same config
    assert {r["id"] for r in data} == {"relatorios-h3"}

    cli_out = CliRunner().invoke(app, ["repos", "--tag", "pro-bono"]).output
    assert "relatorios-h3" in cli_out
    assert "meta-system" not in cli_out


_FAKE_ISSUES = "import json; print(json.dumps([{'number': 5, 'title': 'ISSUE-TITLE'}]))"


def _tracker_config(tmp_path: Path) -> Path:
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


def test_mcp_context_returns_same_composed_join_as_cli(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(_tracker_config(tmp_path)))

    # the task cites the repo, so the tracker scopes its fan-out to it (iris#36)
    data = asyncio.run(_call_context("some task on meta-system#5"))

    # MCP returns the composed repo ⋈ open-issues, off the same composer
    repos = {rw["repo"]["id"]: [i["id"] for i in rw["issues"]] for rw in data["repos"]}
    assert repos == {"meta-system": ["meta-system#5"]}

    # …and it is the SAME join the CLI renders for the same config
    cli_out = CliRunner().invoke(app, ["context", "some task on meta-system#5"]).output
    assert "meta-system#5" in cli_out
    assert "ISSUE-TITLE" in cli_out


_FAKE_TASKS = "import json; print(json.dumps([{'id': 'k9', 'text': 'work meta-system#7 soon'}]))"


def _tasks_config(tmp_path: Path) -> Path:
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


def test_mcp_context_returns_tasks_join_matching_cli(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(_tasks_config(tmp_path)))

    data = asyncio.run(_call_context("some task"))

    # MCP exposes the repo ⋈ tasks join (arm-a), off the same composer as the CLI
    tasks = {rw["repo"]["id"]: [t["id"] for t in rw["tasks"]] for rw in data["repos"]}
    assert tasks == {"meta-system": ["k9"]}

    cli_out = CliRunner().invoke(app, ["context", "some task"]).output
    assert "task ^k9" in cli_out
    assert "work meta-system#7 soon" in cli_out


# --- SP-T6: MCP `inbound` — the same records as the CLI, off the same composer ---------------------

from types import SimpleNamespace  # noqa: E402

import iris.cli as cli  # noqa: E402
import iris.mcp_adapter as mcp_adapter  # noqa: E402
from iris.core.federation import FederationResult  # noqa: E402
from iris.core.model import Node  # noqa: E402

_FAKE_CONFIG = SimpleNamespace(sources=[])

_ITEM = Node(id="iris#34", kind="issue", title="database as a source", roles=["open"], source="tracker")
_TASK = Node(id="8g58ft", kind="task", title="", roles=[], source="notes")  # as the store names it (v2)
_TASK_STATE = Node(id="8g58ft", kind="task", title="chase iris#34 in a TJPA session\nmore", roles=["open"],
                   source="gtd")
_CITE = Node(id="journal/2026-09-04.md#a-block", kind="citation", title="journal/2026-09-04.md#a-block",
             roles=["refs"], source="notes")


def _canned(monkeypatch, module, state=None, citing=None, task_state=None, seen=None):
    """Fake the federation passes: the first chain pass returns `state`, the inbound pass `citing`, and
    the second chain pass (the citing tasks' state, Spec v2) `task_state`. `seen` collects each query."""
    chain_calls = []

    def fake_federate(config, query, *a, **k):
        if seen is not None:
            seen.append((sorted(query.kinds), query.text))
        if "inbound" in query.kinds:
            return citing or FederationResult()
        assert "chain" in query.kinds
        chain_calls.append(query.text)
        if len(chain_calls) == 1:
            return state or FederationResult()
        return task_state or FederationResult()

    monkeypatch.setattr(module, "federate", fake_federate)
    monkeypatch.setattr(module, "_load_config" if module is cli else "active_config", lambda *a, **k: _FAKE_CONFIG)


async def _call_inbound(key: str) -> dict:
    async with Client(mcp) as client:
        result = await client.call_tool("inbound", {"key": key})
    sc = result.structured_content
    return sc.get("result", sc)


def test_mcp_inbound_returns_the_same_records_as_the_cli(monkeypatch):
    state = FederationResult(nodes=[_ITEM])
    citing = FederationResult(nodes=[_TASK, _CITE], degraded=["tracker"])
    task_state = FederationResult(nodes=[_TASK_STATE])
    monkeypatch.setattr("iris._present.inbound_sources", lambda config, registry=None: ["notes"])
    _canned(monkeypatch, mcp_adapter, state, citing, task_state)
    _canned(monkeypatch, cli, state, citing, task_state)

    data = asyncio.run(_call_inbound("iris#34"))
    assert data["key"] == "iris#34" and data["item"]["id"] == "iris#34"
    assert [(t["id"], t["roles"]) for t in data["tasks"]] == [("8g58ft", ["open"])]
    assert [c["id"] for c in data["citations"]] == ["journal/2026-09-04.md#a-block"]
    assert data["unknown"] == ["tracker"]
    assert data["searched"] == ["notes"]
    from iris.core.compose import NOT_COVERED
    assert data["not_covered"] == list(NOT_COVERED)

    out = CliRunner().invoke(cli.app, ["inbound", "iris#34"]).stdout
    assert "^8g58ft" in out and "journal/2026-09-04.md#a-block" in out and "## unknown\ntracker" in out


def test_mcp_inbound_invalid_key_returns_error(monkeypatch):
    _canned(monkeypatch, mcp_adapter)
    data = asyncio.run(_call_inbound("not a key"))
    assert "error" in data



def test_mcp_inbound_marks_an_unresolved_task_state_unknown(monkeypatch):
    # Review finding 1: the CLI's `[state unknown]` has its MCP counterpart, an explicit `state`.
    _canned(monkeypatch, mcp_adapter, FederationResult(nodes=[_ITEM]), FederationResult(nodes=[_TASK]),
            FederationResult())
    data = asyncio.run(_call_inbound("iris#34"))
    assert [(t["id"], t["roles"], t["state"]) for t in data["tasks"]] == [("8g58ft", [], "unknown")]

    _canned(monkeypatch, mcp_adapter, FederationResult(nodes=[_ITEM]), FederationResult(nodes=[_TASK]),
            FederationResult(nodes=[_TASK_STATE]))
    data = asyncio.run(_call_inbound("iris#34"))
    assert [t["state"] for t in data["tasks"]] == ["open"]


# --- SP-T8 (Spec v1.2, iris#61): the MCP `repos` tool filters by the descriptor's system ---


def test_mcp_repos_tag_filter_matches_the_descriptor_system(tmp_path, monkeypatch) -> None:
    body = ""
    for name, system in (("first", "s"), ("second", "t")):
        repo = tmp_path / name
        repo.mkdir()
        (repo / "catalog-info.yaml").write_text(f"spec:\n  system: {system}\n", encoding="utf-8")
        body += f"[{repo}]\ncheckout = x\n\n"
    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(body, encoding="utf-8")
    cfg = tmp_path / "sources.toml"
    cfg.write_text(f'[sources.constellation]\ntype = "constellation"\nmrconfig = "{mrconfig}"\n', encoding="utf-8")
    monkeypatch.setenv("IRIS_CONFIG", str(cfg))

    _, data = asyncio.run(_connect_and_call("s"))

    assert [r["id"] for r in data] == ["first"]
    assert data[0]["tags"] == ["s"]
