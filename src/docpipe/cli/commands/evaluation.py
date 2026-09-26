"""RAG evaluation command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import click


@click.group("evaluate")
def evaluate_group() -> None:
    """Evaluation commands for measuring RAG quality."""


@evaluate_group.command("run")
@click.option("--questions", "questions_file", required=True, help="JSON file with Q&A pairs")
@click.option("--db", required=True, help="Database connection string")
@click.option("--table", required=True, help="Table name in the vector DB")
@click.option(
    "--strategy",
    default="naive",
    type=click.Choice(["naive", "hyde", "multi_query", "parent_document", "hybrid"]),
    show_default=True,
)
@click.option("--llm-provider", required=True, help="LLM provider")
@click.option("--llm-model", required=True, help="LLM model name")
@click.option("--embedding-provider", required=True, help="Embedding provider")
@click.option("--embedding-model", required=True, help="Embedding model name")
@click.option(
    "--metrics",
    default="hit_rate,answer_similarity",
    help="Comma-separated metrics: hit_rate,mrr,faithfulness,answer_similarity",
    show_default=True,
)
@click.option("--output", "-o", default=None, help="Output JSON file (default: stdout)")
def evaluate_run(
    questions_file: str,
    db: str,
    table: str,
    strategy: Literal["naive", "hyde", "multi_query", "parent_document", "hybrid"],
    llm_provider: str,
    llm_model: str,
    embedding_provider: str,
    embedding_model: str,
    metrics: str,
    output: str | None,
) -> None:
    """Evaluate RAG quality using a Q&A file."""
    from docpipe.core.types import EvalConfig, EvalQuestion, RAGConfig
    from docpipe.eval.pipeline import EvalPipeline

    with open(questions_file) as f:
        raw = json.load(f)
    questions = [EvalQuestion(**q) for q in raw]
    metric_list = [m.strip() for m in metrics.split(",")]
    rag_config = RAGConfig(
        connection_string=db,
        table_name=table,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        llm_provider=llm_provider,
        llm_model=llm_model,
        strategy=strategy,
    )
    result = EvalPipeline(
        EvalConfig(rag_config=rag_config, questions=questions, metrics=metric_list)
    ).run()
    m = result.metrics
    click.echo(
        f"\nEvaluation Results ({result.num_questions} questions, {result.timing_seconds:.1f}s)"
    )
    click.echo("-" * 50)
    if m.hit_rate is not None:
        click.echo(f"  hit_rate:          {m.hit_rate:.3f}")
    if m.mrr is not None:
        click.echo(f"  mrr:               {m.mrr:.3f}")
    if m.faithfulness is not None:
        click.echo(f"  faithfulness:      {m.faithfulness:.3f}")
    if m.answer_similarity is not None:
        click.echo(f"  answer_similarity: {m.answer_similarity:.3f}")
    if output:
        Path(output).write_text(result.model_dump_json(indent=2))
        click.echo(f"\nFull results written to {output}")
