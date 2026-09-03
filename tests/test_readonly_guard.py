"""SP-T6 gate (PR4): audit the interface — no Source nor the MCP adapter exposes a
mutation operation. The read-only invariant lives here.

The MCP-adapter arm self-activates once SP-T8 lands (importorskip); until then it is
skipped, and the CLI + sources are audited directly.
"""

from __future__ import annotations

import pytest
from typer.main import get_command

from iris.cli import app
from iris.config import Config, SourceSpec
from iris.core.registry import DEFAULT
from iris.core.source import Source

# Verbs whose presence as an operation would signal a mutation surface.
MUTATION_VERBS = {
    "add", "create", "update", "delete", "remove", "write",
    "set", "edit", "put", "post", "sync", "push", "commit",
    "propose", "confirm", "reject", "stamp", "deposit", "import",
}


def _mutation_names(names) -> set[str]:
    hits = set()
    for name in names:
        base = name.lstrip("_")
        for verb in MUTATION_VERBS:
            if base == verb or base.startswith(verb + "_"):
                hits.add(name)
    return hits


def test_cli_exposes_no_mutation_command() -> None:
    commands = set(get_command(app).commands.keys())
    assert _mutation_names(commands) == set()


def test_source_protocol_has_only_read() -> None:
    members = {m for m in dir(Source) if not m.startswith("_")}
    assert "read" in members
    assert _mutation_names(members) == set()


def test_registered_sources_expose_no_mutation_method() -> None:
    # Resolve the built-in sources and audit their public surface.
    import iris.sources  # noqa: F401  (triggers self-registration)

    config = Config(sources=[SourceSpec("notes", {}, type="cli-json"), SourceSpec("constellation", {})])
    sources = DEFAULT.resolve(config)
    assert sources, "expected built-in sources to be registered"
    for source in sources:
        public = {m for m in dir(source) if not m.startswith("_")}
        assert "read" in public
        assert _mutation_names(public) == set(), f"{source.name} exposes a mutation method"


def test_mcp_adapter_exposes_no_mutation_tool() -> None:
    adapter = pytest.importorskip("iris.mcp_adapter")  # skipped until SP-T8
    names = set(adapter.tool_names())
    assert _mutation_names(names) == set()
