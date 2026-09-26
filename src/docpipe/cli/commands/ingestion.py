"""Vector-store ingestion and search commands."""

from __future__ import annotations

import json
from typing import Literal, cast

import click


@click.command()
@click.argument("file")
@click.option("--db", required=True, help="Database connection string")
@click.option("--table", required=True, help="Target table name")
@click.option(
    "--embedding-provider",
    required=True,
    help="Embedding provider (openai, ollama, huggingface, google)",
)
@click.option("--embedding-model", required=True, help="Embedding model name")
@click.option("--mode", default="both", type=click.Choice(["chunks", "extractions", "both"]))
@click.option("--chunk-size", default=1000, help="Chunk size for text splitting")
@click.option("--chunk-overlap", default=200, help="Chunk overlap")
@click.option("--parser", default="docling", help="Parser to use")
@click.option("--incremental", is_flag=True, help="Skip files already ingested (hash-based)")
def ingest(
    file: str,
    db: str,
    table: str,
    embedding_provider: str,
    embedding_model: str,
    mode: Literal["chunks", "extractions", "both"],
    chunk_size: int,
    chunk_overlap: int,
    parser: str,
    incremental: bool,
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
        incremental=incremental,
    )
    parsed = PluginRegistry.get().get_parser(parser).parse(file)
    result = IngestionPipeline(config).ingest(parsed)
    click.echo(
        f"Skipped '{file}' (unchanged, incremental mode)"
        if result.skipped
        else f"Ingested {result.chunks_ingested} chunks into '{result.table_name}'"
    )
    if result.table_created:
        click.echo("Table was created.")


@click.command()
@click.argument("query")
@click.option("--db", required=True, help="Database connection string")
@click.option("--table", required=True, help="Table name to search")
@click.option("--embedding-provider", required=True, help="Embedding provider")
@click.option("--embedding-model", required=True, help="Embedding model name")
@click.option("--top-k", default=10, help="Number of results")
def search(
    query: str, db: str, table: str, embedding_provider: str, embedding_model: str, top_k: int
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
    results = IngestionPipeline(config).search(query, top_k=top_k)
    for i, result in enumerate(results, 1):
        score = cast(float, result["score"])
        content = cast(str, result["content"])
        metadata = cast(dict[str, object], result["metadata"])
        click.echo(f"\n--- Result {i} (score: {score:.4f}) ---")
        click.echo(content[:500])
        if metadata:
            click.echo(f"Metadata: {json.dumps(metadata, default=str)}")
