"""iris CLI — read-only commands over the federation core.

Skeleton: the command surface exists so ``iris --help`` lists the read-only commands;
the command bodies are implemented in a later task.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="iris",
    help="Sovereign, read-only agent-context layer — federate context sources and serve them to agents.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def repos(tag: str = typer.Option(None, "--tag", help="Filter nodes by tag.")) -> None:
    """List repos/nodes, optionally filtered by tag (read-only)."""
    raise NotImplementedError("implemented in SP-T7")


@app.command()
def ground(query: str = typer.Argument(..., help="The query to ground.")) -> None:
    """Ground a query across federated sources (read-only)."""
    raise NotImplementedError("implemented in SP-T7")


@app.command()
def context(task: str = typer.Argument(..., help="The task to assemble context for.")) -> None:
    """Assemble the integral context relevant to a task (read-only)."""
    raise NotImplementedError("implemented in SP-T7")


def main() -> None:
    """Console-script entry point."""
    app()
