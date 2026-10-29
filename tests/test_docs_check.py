"""SP-T7 gate: the README documents `check` (all drift kinds + exit codes); the example config parses
and names no real org or host."""

from __future__ import annotations

from pathlib import Path

from iris.config import load_config
from iris.core.membership import DRIFT_KINDS

ROOT = Path(__file__).resolve().parent.parent


def test_readme_check_section_lists_every_kind_and_exit_code() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme[readme.index("### `check`"):]
    for kind in DRIFT_KINDS:
        assert f"`{kind}`" in section, kind
    for code in ("**0**", "**1**", "**2**"):
        assert code in section


def test_example_config_parses_with_placeholder_orgs_only() -> None:
    config = load_config(ROOT / "sources.example.toml")
    forge = next(s for s in config.sources if s.type == "forge-repos")
    assert forge.options["host"].startswith("<")
    assert all(org.startswith("<") for org in forge.options["orgs"])
    assert all(slug.startswith("<") for slug in config.check["exclude"])


def test_readme_lists_the_inbound_verb_tool_and_stanza() -> None:
    # item-inbound-context SP-T7: the verb in the command list, the MCP tool, and the cli-json stanza.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    cli = readme[readme.index("## Use — CLI"):readme.index("## Use — MCP")]
    assert "iris inbound <key>" in cli
    assert "tool **`inbound(key)`**" in readme[readme.index("## Use — MCP"):]
    assert "[sources.notes.inbound]" in readme


def test_example_config_declares_an_inbound_stanza() -> None:
    config = load_config(ROOT / "sources.example.toml")
    notes = next(s for s in config.sources if s.type == "cli-json")
    assert "{key}" in notes.options["inbound"]["command"]
    assert notes.options["inbound"]["map"]["locator"]
