"""iris CLI — read-only commands over the federation core."""

from __future__ import annotations

import json

import typer

import iris.sources  # noqa: F401  (registers the built-in sources)
from iris.config import Config, active_config
from iris._present import relevant_repos
from iris.core.compose import compose_inbound, compose_referenced_nodes, compose_repo_issues, is_gate_marked
from iris.core.federation import FederationResult, federate
from iris.core.membership import compose_membership
from iris.core.model import Node
from iris.core.source import KIND_CHAIN, KIND_HITS, KIND_INBOUND, KIND_NODES, KIND_UNIVERSE, Query
from iris.sources._repos import parse_key
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
    # Relevance-scope the display to the repos that actually participate in a join for this task —
    # dropping join-less repos and multi-repo task scatter (iris#38). The composer keeps the full
    # roster; scoping is a presentation concern, shared with the MCP adapter for parity.
    relevant = relevant_repos(composed, task)
    if relevant:
        typer.echo("## repos")
        for rw in relevant:
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
        "context",
        task,
        hits=len(result.hits),
        nodes=len(composed.repos),
        sources=_source_names(config),
        # Identity-miss counts (Brief F6): durably record the deferred protocol's arming signal.
        extra={
            "unmatched_issues": len(composed.unmatched),
            "unmatched_tasks": len(composed.unmatched_tasks),
        },
    )


def _ref_label(node: Node) -> str:
    """Display a node by its reference form — ``^<id>`` for an anchor task, ``<slug>#<n>`` for an issue."""
    return f"^{node.id}" if node.kind == "task" else node.id


@app.command()
def chain(item: str = typer.Argument(..., help="A work item's text (it carries `token#N` / `^anchor` refs).")) -> None:
    """Resolve a work item's cross-repo dependency chain in one shot (read-only).

    Parses the `<repo>#<n>` and `^<anchor>` refs in the item's prose, fetches each referenced node's
    LIVE state across the repos, and surfaces the OPEN ones as data-derived candidate blockers — YOU
    judge the actual blocker. Refs it cannot resolve are shown as UNKNOWN, never folded into 'clear'.
    """
    config = _load_config()
    result = federate(config, Query(text=item, kinds=frozenset({KIND_CHAIN})))
    composed = compose_referenced_nodes(item, result)

    if composed.blocker_candidates:
        typer.echo("## candidate blockers (OPEN — you judge the actual blocker)")
        for node in composed.blocker_candidates:
            mark = "  [gate]" if is_gate_marked(node) else ""
            typer.echo(f"  - {_ref_label(node)}  {_oneline(node.title)}{mark}")
    skip_ids = {id(n) for n in composed.blocker_candidates} | {id(n) for n in composed.state_unknown}
    nonblockers = [n for n in composed.resolved if id(n) not in skip_ids]
    if nonblockers:
        typer.echo("## resolved (not blocking)")
        for node in nonblockers:
            typer.echo(f"  - {_ref_label(node)}  [{'/'.join(node.roles)}]  {_oneline(node.title)}")
    if composed.state_unknown:
        typer.echo("## unknown state — resolved but state undetermined (not confirmed clear)")
        for node in composed.state_unknown:
            typer.echo(f"  - {_ref_label(node)}  {_oneline(node.title)}")
    if composed.unresolved:
        typer.echo("## unknown — could NOT resolve (not confirmed clear)")
        for ref in composed.unresolved:
            typer.echo(f"  - {ref}")
    # Failure-mode guard: only claim no-open-blockers when NOTHING is unknown (neither unresolved refs
    # nor resolved-but-stateless nodes).
    if (
        composed.resolved
        and not composed.blocker_candidates
        and not composed.unresolved
        and not composed.state_unknown
    ):
        typer.echo("## no open blockers among the resolved refs")
    if not composed.resolved and not composed.unresolved:
        typer.echo("# no refs found in the item text", err=True)

    _emit_notes(result)
    log_request(
        "chain",
        item,
        hits=0,
        nodes=len(composed.resolved),
        sources=_source_names(config),
        extra={
            "blocker_candidates": len(composed.blocker_candidates),
            "unresolved": len(composed.unresolved),
        },
    )


@app.command()
def inbound(key: str = typer.Argument(..., help="One item key: `<repo>#<n>` or `^<anchor>`.")) -> None:
    """Show what cites one item, joined to its live state (read-only).

    Reads the item's state, the tasks whose text references it, and the store records that link to it.
    A source that could not be read is listed under UNKNOWN — never folded into 'no citations'.
    """
    if parse_key(key) is None:
        typer.echo(f"invalid key {key!r}: expected exactly one `<repo>#<n>` or `^<anchor>`", err=True)
        raise typer.Exit(2)
    config = _load_config()
    state = federate(config, Query(text=key, kinds=frozenset({KIND_CHAIN})))
    citing = federate(config, Query(text=key, kinds=frozenset({KIND_INBOUND})))
    composed = compose_inbound(key, state, citing)

    typer.echo("## item")
    if composed.item is None:
        typer.echo(f"{composed.key}  unknown — could not resolve")
    else:
        roles = f"  [{'/'.join(composed.item.roles)}]" if composed.item.roles else ""
        typer.echo(f"{composed.key}{roles}  {_oneline(composed.item.title)}")
    if composed.tasks:
        typer.echo(f"## tasks citing {composed.key}")
        for node in composed.tasks:
            typer.echo(f"^{node.id}  [{'/'.join(node.roles)}]  {_oneline(node.title)}")
    if composed.citations:
        typer.echo("## citations")
        for node in composed.citations:
            typer.echo(f"{node.id}  [{'/'.join(node.roles)}]")
    if composed.unknown:
        typer.echo("## unknown")
        for name in composed.unknown:
            typer.echo(name)
    elif not composed.tasks and not composed.citations:
        typer.echo(f"# no records cite {composed.key}", err=True)

    for note in composed.notes:
        typer.echo(f"# {note}", err=True)
    log_request(
        "inbound",
        key,
        hits=0,
        nodes=len(composed.tasks) + len(composed.citations),
        sources=_source_names(config),
        extra={"unknown": len(composed.unknown)},
    )


@app.command()
def check(as_json: bool = typer.Option(False, "--json", help="Emit the report as JSON.")) -> None:
    """Check constellation membership for drift (read-only).

    Reads the repo universe (registry, on-disk roots, forge orgs) and reports each drift kind found.
    Exit code: 0 = no drift and every dimension ran; 1 = drift found; 2 = no drift found but a
    dimension was skipped (never reported as clean).
    """
    config = _load_config()
    result = federate(config, Query(kinds=frozenset({KIND_UNIVERSE})))
    report = compose_membership(result, config.check)
    if as_json:
        payload = {
            "drift": [{"kind": i.kind, "subject": i.subject, "detail": i.detail} for i in report.items],
            "skipped": report.skipped,
            "counts": report.counts,
        }
        typer.echo(json.dumps(payload, indent=2))
    else:
        current = None
        for item in report.items:
            if item.kind != current:
                current = item.kind
                typer.echo(f"## {item.kind}")
            typer.echo(f"- {item.subject}  {item.detail}")
        for skip in report.skipped:
            typer.echo(f"# skipped: {skip}", err=True)
        counts = ", ".join(f"{v} {k}" for k, v in report.counts.items())
        if report.items:
            kinds = len({i.kind for i in report.items})
            typer.echo(f"drift: {len(report.items)} item(s) across {kinds} kind(s) ({counts})")
        elif report.skipped:
            typer.echo(f"no drift found, but {len(report.skipped)} dimension(s) skipped — result incomplete ({counts})")
        else:
            typer.echo(f"clean ({counts})")
    _emit_notes(result)
    log_request(
        "check",
        "",
        hits=0,
        nodes=report.counts.get("members", 0),
        sources=_source_names(config),
        extra={"drift": len(report.items), "skipped": len(report.skipped)},
    )
    if report.items:
        raise typer.Exit(1)
    if report.skipped:
        raise typer.Exit(2)


def main() -> None:
    """Console-script entry point."""
    app()
