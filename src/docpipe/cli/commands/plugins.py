"""Plugin listing and source recommendation commands."""

from __future__ import annotations

import json
from pathlib import Path

import click


@click.group("plugins")
def plugins() -> None:
    """Manage plugins."""


def _print_plugin_group(registry: object, group: str) -> None:
    from docpipe.profiles.guardrails import enrich_plugin_info

    list_method = getattr(registry, f"list_{group}")
    info_method = getattr(registry, f"{group[:-1]}_info")
    click.echo(f"{group.title()}:")
    for name in list_method():
        info = enrich_plugin_info(group, name, info_method(name))
        status = "available" if info.get("available") else "not installed"
        allowed = "allowed" if info.get("allowed") else "denied"
        click.echo(f"  - {name} ({status}, {allowed}, tier={info.get('tier') or '-'})")


@plugins.command("list")
def plugins_list() -> None:
    """List all registered plugins."""
    from docpipe.registry.registry import PluginRegistry

    registry = PluginRegistry.get()
    for group in ("parsers", "extractors", "chunkers", "rerankers", "evaluators"):
        _print_plugin_group(registry, group)
        click.echo("")


@click.command("resolve")
@click.argument("source")
@click.option(
    "--goal",
    default="ingest",
    type=click.Choice(["ingest", "rag", "parse", "agents"]),
    show_default=True,
)
@click.option("--preset", default=None, help="Optional runtime preset override")
@click.option("--output", "-o", default=None, help="Write JSON to file")
def resolve_plugins(source: str, goal: str, preset: str | None, output: str | None) -> None:
    """Recommend parser/chunker/reranker for a source and goal."""
    from docpipe.profiles.resolve import resolve_recommendation

    content = json.dumps(resolve_recommendation(source=source, goal=goal, preset=preset), indent=2)
    if output:
        Path(output).write_text(content)
        click.echo(f"Wrote recommendations to {output}")
    else:
        click.echo(content)
