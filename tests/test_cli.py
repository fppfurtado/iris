"""SP-T1 gate: ``iris --help`` lists read-only commands and exposes no mutation command."""

from __future__ import annotations

from typer.main import get_command
from typer.testing import CliRunner

from iris.cli import app

runner = CliRunner()

READ_ONLY_COMMANDS = {"repos", "ground", "context"}
# Verbs whose presence as a command would signal a mutation surface.
MUTATION_VERBS = {
    "add", "create", "update", "delete", "remove", "write",
    "set", "edit", "put", "post", "sync", "push", "commit",
}


def test_help_lists_read_only_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in READ_ONLY_COMMANDS:
        assert cmd in result.output


def test_no_mutation_command_exposed() -> None:
    names = set(get_command(app).commands.keys())
    assert names == READ_ONLY_COMMANDS
    assert not (names & MUTATION_VERBS)
