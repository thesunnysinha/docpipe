"""Configuration template generation command."""

from __future__ import annotations

from pathlib import Path

import click


@click.group("config")
def config() -> None:
    """Manage configuration."""


@config.command("init")
@click.option("--output", "-o", default="docpipe.yaml", help="Output file path")
def config_init(output: str) -> None:
    """Generate a template configuration file."""
    template = """\
# docpipe configuration
# See https://github.com/thesunnysinha/docpipe for documentation

# Parser settings
default_parser: docling
parser_options: {}

# Extractor settings
default_extractor: langextract
extractor_options: {}

# Ingestion settings (provide your own DB connection)
# db_connection_string: postgresql://user:pass@host:5432/dbname
# db_table_name: docpipe_documents
# embedding_provider: openai
# embedding_model: text-embedding-3-small
# chunk_size: 1000
# chunk_overlap: 200
# ingest_mode: both

# Server settings
server_host: "0.0.0.0"
server_port: 8000

# Pipeline settings
max_concurrency: 4

# Logging
log_level: INFO
"""
    Path(output).write_text(template)
    click.echo(f"Config template written to {output}")
