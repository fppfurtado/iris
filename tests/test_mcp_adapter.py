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

    data = asyncio.run(_call_context("some task"))

    # MCP returns the composed repo ⋈ open-issues, off the same composer
    repos = {rw["repo"]["id"]: [i["id"] for i in rw["issues"]] for rw in data["repos"]}
    assert repos == {"meta-system": ["meta-system#5"]}

    # …and it is the SAME join the CLI renders for the same config
    cli_out = CliRunner().invoke(app, ["context", "some task"]).output
    assert "meta-system#5" in cli_out
    assert "ISSUE-TITLE" in cli_out
