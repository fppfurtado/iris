"""SP-T8 gate: an MCP client connects, lists read-only tools, and gets the SAME
result as the CLI."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastmcp import Client
from typer.testing import CliRunner

from iris.cli import app
from iris.mcp_adapter import mcp


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


async def _connect_and_call(tag: str) -> tuple[set[str], list[dict]]:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        result = await client.call_tool("repos", {"tag": tag})
    return {t.name for t in tools}, result.structured_content["result"]


def test_mcp_client_lists_read_only_tools_and_matches_cli(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(_fixture_config(tmp_path)))

    names, data = asyncio.run(_connect_and_call("pro-bono"))

    # an MCP client connected and saw the read-only tools
    assert {"ground", "repos"} <= names

    # the tool returns the pro-bono repo — SAME as the CLI for the same config
    assert {r["id"] for r in data} == {"relatorios-h3"}

    cli_out = CliRunner().invoke(app, ["repos", "--tag", "pro-bono"]).output
    assert "relatorios-h3" in cli_out
    assert "meta-system" not in cli_out
