"""iris CLI — read-only commands over the federation core."""

from __future__ import annotations

import typer

import iris.sources  # noqa: F401  (registers the built-in sources)
from iris.config import Config, active_config
from iris.core.compose import compose_repo_issues
from iris.core.federation import FederationResult, federate
from iris.core.source import KIND_HITS, KIND_NODES, Query
from iris.telemetry import log_request

app = typer.Typer(
    name="iris",
    help="Sovereign, read-only agent-context layer — federate context sources and serve them to agents.",
    no_args_is_help=True,
    add_completion=False,
)


def _load_config() -> Config:
    return active_config()


def _source_names(config: Config) -> list[str]:
    return [spec.name for spec in config.sources]


def _emit_notes(result: FederationResult) -> None:
    for note in result.notes:
        typer.echo(f"# {note}", err=True)


def _oneline(text: str, width: int = 100) -> str:
    """First line of a task's text, capped — GTD items carry a full paragraph as their title."""
    head = text.strip().splitlines()[0] if text.strip() else ""
    return head if len(head) <= width else head[: width - 1] + "…"


@app.command()
def repos(tag: str = typer.Option(None, "--tag", help="Filter repos by tag.")) -> None:
    """List repos with their tags/roles, optionally filtered by tag (read-only)."""
    config = _load_config()
    result = federate(config, Query(tag=tag, kinds=frozenset({KIND_NODES})))
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
    log_request("repos", tag or "", hits=0, nodes=len(nodes), sources=_source_names(config))


@app.command()
def ground(query: str = typer.Argument(..., help="The query to ground.")) -> None:
    """Ground a query across federated sources (read-only)."""
    config = _load_config()
    result = federate(config, Query(text=query, kinds=frozenset({KIND_HITS})))
    for hit in result.hits:
        suffix = f"  ({hit.trust}{' · ' + hit.age if hit.age else ''})" if hit.trust else ""
        typer.echo(f"{hit.ref}{suffix}")
        if hit.excerpt:
            typer.echo(f"  {hit.excerpt}")
    _emit_notes(result)
    log_request("ground", query, hits=len(result.hits), nodes=0, sources=_source_names(config))


@app.command()
def context(task: str = typer.Argument(..., help="The task to assemble context for.")) -> None:
    """Assemble the integral context relevant to a task (read-only).

    Synthesizes repos ⋈ their open issues AND the standing tasks that reference them (the cross-source
    joins) plus grounding on the task's terms, in one pass.
    """
    config = _load_config()
    result = federate(config, Query(text=task, kinds=frozenset({KIND_NODES, KIND_HITS})))
    composed = compose_repo_issues(result)
    if composed.repos:
        typer.echo("## repos")
        for rw in composed.repos:
            tags = f"  [{', '.join(rw.repo.tags)}]" if rw.repo.tags else ""
            typer.echo(f"{rw.repo.id}{tags}")
            for issue in rw.issues:
                typer.echo(f"  - issue {issue.id}  {issue.title}")
            for gtd in rw.tasks:
                typer.echo(f"  - task ^{gtd.id}  {_oneline(gtd.title)}")
    if composed.unmatched:
        typer.echo("## unmatched issues")
        for issue in composed.unmatched:
            typer.echo(f"  - {issue.id}  {issue.title}")
    if composed.unmatched_tasks:
        typer.echo("## tasks referencing repos outside the constellation")
        for gtd in composed.unmatched_tasks:
            typer.echo(f"  - ^{gtd.id}  {_oneline(gtd.title)}")
    if result.hits:
        typer.echo("## grounding")
        for hit in result.hits:
            typer.echo(f"{hit.ref}")
            if hit.excerpt:
                typer.echo(f"  {hit.excerpt}")
    _emit_notes(result)
    for note in composed.notes:
        typer.echo(f"# {note}", err=True)
    log_request(
        "context", task, hits=len(result.hits), nodes=len(composed.repos), sources=_source_names(config)
    )


def main() -> None:
    """Console-script entry point."""
    app()
