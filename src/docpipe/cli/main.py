"""Root Click group and stable public entry point for the Docpipe CLI."""

from __future__ import annotations

import logging

import click

from docpipe._version import __version__
from docpipe.cli.commands.config import config, config_init  # noqa: F401
from docpipe.cli.commands.documents import extract, parse, run_pipeline
from docpipe.cli.commands.evaluation import evaluate_group, evaluate_run  # noqa: F401
from docpipe.cli.commands.ingestion import ingest, search
from docpipe.cli.commands.plugins import (  # noqa: F401
    _print_plugin_group,
    plugins,
    plugins_list,
    resolve_plugins,
)
from docpipe.cli.commands.profiles import profiles, profiles_list  # noqa: F401
from docpipe.cli.commands.rag import rag, rag_query  # noqa: F401
from docpipe.cli.commands.server import serve


@click.group()
@click.version_option(__version__, prog_name="docpipe")
@click.option("--log-level", default="INFO", help="Logging level")
def cli(log_level: str) -> None:
    """docpipe - Unified document parsing, extraction, and ingestion pipeline."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


for command in (
    parse,
    extract,
    run_pipeline,
    ingest,
    search,
    serve,
    plugins,
    profiles,
    resolve_plugins,
    config,
    rag,
    evaluate_group,
):
    cli.add_command(command)


if __name__ == "__main__":
    cli()
