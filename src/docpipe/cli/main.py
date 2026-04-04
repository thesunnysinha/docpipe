"""CLI interface for docpipe."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

from docpipe._version import __version__


@click.group()
@click.version_option(__version__, prog_name="docpipe")
@click.option("--log-level", default="INFO", help="Logging level")
def cli(log_level: str) -> None:
    """docpipe - Unified document parsing, extraction, and ingestion pipeline."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


@cli.command()
@click.argument("file")
@click.option("--parser", default="docling", help="Parser to use")
@click.option(
    "--format", "output_format", default="markdown",
    type=click.Choice(["markdown", "text", "json"]),
)
@click.option("--output", "-o", default=None, help="Output file (default: stdout)")
def parse(file: str, parser: str, output_format: str, output: str | None) -> None:
    """Parse a document into structured text."""
    from docpipe.registry.registry import PluginRegistry

    p = PluginRegistry.get().get_parser(parser)
    result = p.parse(file)

    if output_format == "markdown":
        content = result.markdown or result.text
    elif output_format == "text":
        content = result.text
    else:
        content = result.model_dump_json(indent=2)

    if output:
        Path(output).write_text(content)
        click.echo(f"Output written to {output}")
    else:
        click.echo(content)


@cli.command()
@click.argument("text_or_file")
@click.option("--schema", "schema_file", required=True, help="Schema YAML file")
@click.option("--extractor", default="langextract", help="Extractor to use")
@click.option("--model", "model_id", required=True, help="LLM model ID")
@click.option("--output", "-o", default=None, help="Output file (default: stdout)")
def extract(
    text_or_file: str,
    schema_file: str,
    extractor: str,
    model_id: str,
    output: str | None,
) -> None:
    """Extract structured data from text or a file."""
    import yaml

    from docpipe.core.types import ExtractionSchema
    from docpipe.registry.registry import PluginRegistry

    # Load schema
    with open(schema_file) as f:
        schema_data = yaml.safe_load(f)
    schema_data["model_id"] = model_id
    schema = ExtractionSchema(**schema_data)

    # Determine if input is a file or text
    text = text_or_file
    if Path(text_or_file).exists():
        text = Path(text_or_file).read_text()

    e = PluginRegistry.get().get_extractor(extractor)
    results = e.extract(text, schema)

    output_data = [r.model_dump() for r in results]
    content = json.dumps(output_data, indent=2, default=str)

    if output:
        Path(output).write_text(content)
        click.echo(f"Output written to {output}")
    else:
        click.echo(content)


@cli.command("run")
@click.argument("file")
@click.option("--schema", "schema_file", required=True, help="Schema YAML file")
@click.option("--parser", default="docling", help="Parser to use")
@click.option("--extractor", default="langextract", help="Extractor to use")
@click.option("--model", "model_id", required=True, help="LLM model ID")
@click.option("--output", "-o", default=None, help="Output file (default: stdout)")
def run_pipeline(
    file: str,
    schema_file: str,
    parser: str,
    extractor: str,
    model_id: str,
    output: str | None,
) -> None:
    """Run the full pipeline: parse + extract."""
    import yaml

    from docpipe.core.pipeline import Pipeline
    from docpipe.core.types import ExtractionSchema

    with open(schema_file) as f:
        schema_data = yaml.safe_load(f)
    schema_data["model_id"] = model_id
    schema = ExtractionSchema(**schema_data)

    pipeline = Pipeline(parser=parser, extractor=extractor)
    result = pipeline.run(file, schema)

    content = result.model_dump_json(indent=2)

    if output:
        Path(output).write_text(content)
        click.echo(f"Output written to {output}")
    else:
        click.echo(content)


@cli.command()
@click.argument("file")
@click.option("--db", required=True, help="Database connection string")
@click.option("--table", required=True, help="Target table name")
@click.option(
    "--embedding-provider", required=True,
    help="Embedding provider (openai, ollama, huggingface, google)",
)
@click.option("--embedding-model", required=True, help="Embedding model name")
@click.option("--mode", default="both", type=click.Choice(["chunks", "extractions", "both"]))
@click.option("--chunk-size", default=1000, help="Chunk size for text splitting")
@click.option("--chunk-overlap", default=200, help="Chunk overlap")
@click.option("--parser", default="docling", help="Parser to use")
def ingest(
    file: str,
    db: str,
    table: str,
    embedding_provider: str,
    embedding_model: str,
    mode: str,
    chunk_size: int,
    chunk_overlap: int,
    parser: str,
) -> None:
    """Parse a document and ingest into a vector database."""
    from docpipe.core.types import IngestionConfig
    from docpipe.ingestion.pipeline import IngestionPipeline
    from docpipe.registry.registry import PluginRegistry

    config = IngestionConfig(
        connection_string=db,
        table_name=table,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        ingest_mode=mode,
    )

    p = PluginRegistry.get().get_parser(parser)
    parsed = p.parse(file)

    ingestion = IngestionPipeline(config)
    result = ingestion.ingest(parsed)

    click.echo(f"Ingested {result.chunks_ingested} chunks into '{result.table_name}'")
    if result.table_created:
        click.echo("Table was created.")


@cli.command()
@click.argument("query")
@click.option("--db", required=True, help="Database connection string")
@click.option("--table", required=True, help="Table name to search")
@click.option("--embedding-provider", required=True, help="Embedding provider")
@click.option("--embedding-model", required=True, help="Embedding model name")
@click.option("--top-k", default=10, help="Number of results")
def search(
    query: str,
    db: str,
    table: str,
    embedding_provider: str,
    embedding_model: str,
    top_k: int,
) -> None:
    """Search for similar documents in the vector database."""
    from docpipe.core.types import IngestionConfig
    from docpipe.ingestion.pipeline import IngestionPipeline

    config = IngestionConfig(
        connection_string=db,
        table_name=table,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
    )

    ingestion = IngestionPipeline(config)
    results = ingestion.search(query, top_k=top_k)

    for i, r in enumerate(results, 1):
        click.echo(f"\n--- Result {i} (score: {r['score']:.4f}) ---")
        click.echo(r["content"][:500])
        if r["metadata"]:
            click.echo(f"Metadata: {json.dumps(r['metadata'], default=str)}")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8000, help="Server port")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the docpipe API server."""
    try:
        import uvicorn
    except ImportError:
        click.echo("Server requires uvicorn. Install with: pip install docpipe[server]", err=True)
        sys.exit(1)

    click.echo(f"Starting docpipe server on {host}:{port}")
    uvicorn.run("docpipe.server.app:app", host=host, port=port, reload=reload)


@cli.group()
def plugins() -> None:
    """Manage plugins."""


@plugins.command("list")
def plugins_list() -> None:
    """List all registered plugins."""
    from docpipe.registry.registry import PluginRegistry

    registry = PluginRegistry.get()

    click.echo("Parsers:")
    for name in registry.list_parsers():
        info = registry.parser_info(name)
        available = "available" if info.get("available") else "not installed"
        click.echo(f"  - {name} ({available})")

    click.echo("\nExtractors:")
    for name in registry.list_extractors():
        info = registry.extractor_info(name)
        available = "available" if info.get("available") else "not installed"
        click.echo(f"  - {name} ({available})")


@cli.group()
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


if __name__ == "__main__":
    cli()
