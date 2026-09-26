"""Retrieval-augmented generation query command."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import click


@click.group("rag")
def rag() -> None:
    """RAG (Retrieval-Augmented Generation) commands."""


@rag.command("query")
@click.argument("question")
@click.option("--db", required=True, help="Database connection string")
@click.option("--table", required=True, help="Table name in the vector DB")
@click.option(
    "--strategy",
    default="naive",
    type=click.Choice(["naive", "hyde", "multi_query", "parent_document", "hybrid"]),
    show_default=True,
    help="Retrieval strategy",
)
@click.option(
    "--llm-provider", required=True, help="LLM provider (openai, google, ollama, anthropic)"
)
@click.option("--llm-model", required=True, help="LLM model name")
@click.option("--embedding-provider", required=True, help="Embedding provider")
@click.option("--embedding-model", required=True, help="Embedding model name")
@click.option("--top-k", default=5, show_default=True, help="Number of chunks to retrieve")
@click.option(
    "--reranker",
    default="none",
    type=click.Choice(["none", "flashrank", "cohere"]),
    show_default=True,
    help="Optional reranker",
)
@click.option("--output", "-o", default=None, help="Output JSON file (default: stdout)")
def rag_query(
    question: str,
    db: str,
    table: str,
    strategy: Literal["naive", "hyde", "multi_query", "parent_document", "hybrid"],
    llm_provider: str,
    llm_model: str,
    embedding_provider: str,
    embedding_model: str,
    top_k: int,
    reranker: Literal["none", "flashrank", "cohere"],
    output: str | None,
) -> None:
    """Answer a question using RAG against a vector database."""
    from docpipe.core.types import RAGConfig
    from docpipe.rag.pipeline import RAGPipeline

    config = RAGConfig(
        connection_string=db,
        table_name=table,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        llm_provider=llm_provider,
        llm_model=llm_model,
        strategy=strategy,
        top_k=top_k,
        reranker=reranker,
    )
    result = RAGPipeline(config).query(question)
    click.echo(f"\nAnswer  [{result.strategy}, {result.timing_seconds:.2f}s]")
    click.echo("-" * 60)
    click.echo(result.answer)
    click.echo(f"\nSources ({len(result.sources)}):")
    for src in result.sources:
        click.echo(f"  - {src}")
    click.echo(f"Chunks retrieved: {len(result.chunks)}")
    if output:
        Path(output).write_text(result.model_dump_json(indent=2))
        click.echo(f"\nFull result written to {output}")
