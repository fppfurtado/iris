"""SP-T9 gate (S2 proof): the origin question is answered in one interaction via BOTH
the CLI and MCP, with the same answer — the walking-skeleton proof."""

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


async def _mcp_answer(tag: str) -> list[dict]:
    async with Client(mcp) as client:
        result = await client.call_tool("repos", {"tag": tag})
    return result.structured_content["result"]


def test_origin_question_answered_in_one_interaction_both_surfaces(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(_fixture_config(tmp_path)))

    # ONE CLI interaction answers the origin question.
    cli = CliRunner().invoke(app, ["repos", "--tag", "pro-bono"])
    assert cli.exit_code == 0
    assert "relatorios-h3" in cli.output
    assert "meta-system" not in cli.output

    # ONE MCP interaction answers the same question with the SAME answer.
    mcp_ids = {r["id"] for r in asyncio.run(_mcp_answer("pro-bono"))}
    assert mcp_ids == {"relatorios-h3"}
