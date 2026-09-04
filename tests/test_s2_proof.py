"""SP-T9 gate (S2 proof): the origin question is answered in one interaction via BOTH
the CLI and MCP, with the same answer — the walking-skeleton proof.

Also (SP-T5, Brief C7/S2): the `tracker` adapter is source-agnostic by construction — it hardcodes
no forge command and names no org/host/instance; the concrete forge + its coordinates arrive only via
config (and the checkout's own git remote)."""

from __future__ import annotations

import asyncio
import inspect

from fastmcp import Client
from typer.testing import CliRunner

import iris.sources.tracker as tracker_mod
from iris.cli import app
from iris.mcp_adapter import mcp
from iris.sources.tracker import TrackerSource


async def _mcp_answer(tag: str) -> list[dict]:
    async with Client(mcp) as client:
        result = await client.call_tool("repos", {"tag": tag})
    return result.structured_content["result"]


def test_origin_question_answered_in_one_interaction_both_surfaces(constellation_config, monkeypatch) -> None:
    monkeypatch.setenv("IRIS_CONFIG", str(constellation_config))

    # ONE CLI interaction answers the origin question.
    cli = CliRunner().invoke(app, ["repos", "--tag", "pro-bono"])
    assert cli.exit_code == 0
    assert "relatorios-h3" in cli.output
    assert "meta-system" not in cli.output

    # ONE MCP interaction answers the same question with the SAME answer.
    mcp_ids = {r["id"] for r in asyncio.run(_mcp_answer("pro-bono"))}
    assert mcp_ids == {"relatorios-h3"}


def test_tracker_adapter_is_source_agnostic() -> None:
    # Structural proof: the adapter bakes in NO forge — the command is empty until config supplies it.
    src = TrackerSource("tracker")
    assert src._command == []
    assert src._map == {}

    # Leak-check (Brief C7): the adapter module names no concrete org / host / private instance.
    source_text = inspect.getsource(tracker_mod).lower()
    for forbidden in ("github.com", "gitlab.", ".jus.br", "fppfurtado"):
        assert forbidden not in source_text, f"tracker adapter names a private instance: {forbidden!r}"
