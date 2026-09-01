"""iris CLI — read-only commands over the federation core."""

from __future__ import annotations

import typer

import iris.sources  # noqa: F401  (registers the built-in sources)
from iris.config import Config, active_config
from iris.core.federation import FederationResult, federate
from iris.core.source import KIND_HITS, KIND_NODES, Query

app = typer.Typer(
    name="iris",
    help="Sovereign, read-only agent-context layer — federate context sources and serve them to agents.",
    no_args_is_help=True,
    add_completion=False,
)


def _load_config() -> Config:
    return active_config()


def _emit_notes(result: FederationResult) -> None:
    for note in result.notes:
        typer.echo(f"# {note}", err=True)


@app.command()
def repos(tag: str = typer.Option(None, "--tag", help="Filter repos by tag.")) -> None:
    """List repos with their tags/roles, optionally filtered by tag (read-only)."""
    result = federate(_load_config(), Query(tag=tag, kinds=frozenset({KIND_NODES})))
    nodes = [n for n in result.nodes if n.kind == "repo"]
    if tag:
        nodes = [n for n in nodes if tag in n.tags]
    for node in nodes:
        line = node.id
        if node.tags:
            line += f"  [{', '.join(node.tags)}]"
        if node.roles:
            line += f"  ({', '.join(node.roles)})"
        typer.echo(line)
    _emit_notes(result)


@app.command()
def ground(query: str = typer.Argument(..., help="The query to ground.")) -> None:
    """Ground a query across federated sources (read-only)."""
    result = federate(_load_config(), Query(text=query, kinds=frozenset({KIND_HITS})))
    for hit in result.hits:
        suffix = f"  ({hit.trust}{' · ' + hit.age if hit.age else ''})" if hit.trust else ""
        typer.echo(f"{hit.ref}{suffix}")
        if hit.excerpt:
            typer.echo(f"  {hit.excerpt}")
    _emit_notes(result)


@app.command()
def context(task: str = typer.Argument(..., help="The task to assemble context for.")) -> None:
    """Assemble the integral context relevant to a task (read-only).

    Fase 1 heuristic: the repos+tags plus grounding on the task's terms, in one pass.
    """
    result = federate(_load_config(), Query(text=task, kinds=frozenset({KIND_NODES, KIND_HITS})))
    repos_ = [n for n in result.nodes if n.kind == "repo"]
    if repos_:
        typer.echo("## repos")
        for node in repos_:
            tags = f"  [{', '.join(node.tags)}]" if node.tags else ""
            typer.echo(f"{node.id}{tags}")
    if result.hits:
        typer.echo("## grounding")
        for hit in result.hits:
            typer.echo(f"{hit.ref}")
            if hit.excerpt:
                typer.echo(f"  {hit.excerpt}")
    _emit_notes(result)


def main() -> None:
    """Console-script entry point."""
    app()
