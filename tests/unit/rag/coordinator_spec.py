"""Tests for RAG sequencing independent of vector and model vendors."""

from __future__ import annotations

import logging

import pytest

from docpipe.core.types import RAGChunk, TokenUsage
from docpipe.rag.coordinator import RAGCoordinator, RAGOptions
from docpipe.rag.generation import GeneratedAnswer
from docpipe.rag.retrieval.base import RetrievalResult
from docpipe.rag.retrieval.registry import StrategyRegistry


class StrategyDouble:
    name = "naive"

    async def retrieve(self, question: str) -> RetrievalResult:
        return RetrievalResult(
            (
                RAGChunk(content="private first", score=0.9, source="a.pdf"),
                RAGChunk(content="private second", score=0.8, source="a.pdf"),
                RAGChunk(content="private third", score=0.7, source="b.pdf"),
            ),
            {"strategy_note": "safe"},
        )


class RerankerDouble:
    def __init__(self) -> None:
        self.called = False

    async def rerank(
        self,
        question: str,
        chunks: tuple[RAGChunk, ...],
        *,
        top_n: int,
    ) -> tuple[RAGChunk, ...]:
        self.called = True
        return chunks[:top_n]


class GeneratorDouble:
    def __init__(self) -> None:
        self.context = ""

    async def generate(self, question: str, context: str) -> GeneratedAnswer:
        self.context = context
        return GeneratedAnswer(
            "answer",
            usage=TokenUsage(input_tokens=4, output_tokens=2, total_tokens=6),
        )


@pytest.mark.asyncio
async def test_coordinator_retrieves_reranks_caps_generates_and_logs_safely(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reranker = RerankerDouble()
    generator = GeneratorDouble()
    coordinator = RAGCoordinator(
        options=RAGOptions(
            strategy="naive",
            top_k=3,
            max_chunks_per_source=1,
            rerank_top_n=3,
        ),
        strategies=StrategyRegistry((StrategyDouble(),)),
        generator=generator,
        reranker=reranker,
    )

    with caplog.at_level(logging.INFO):
        result = await coordinator.query("private question")

    assert result.answer == "answer"
    assert [chunk.source for chunk in result.chunks] == ["a.pdf", "b.pdf"]
    assert result.sources == ["a.pdf", "b.pdf"]
    assert result.usage is not None and result.usage.total_tokens == 6
    assert result.metadata["strategy_note"] == "safe"
    assert reranker.called
    assert "Source: a.pdf" in generator.context
    assert "private question" not in caplog.text
    assert "private first" not in caplog.text
    events = {record.__dict__.get("event") for record in caplog.records}
    assert {"rag.retrieval.completed", "rag.generation.completed"} <= events


@pytest.mark.asyncio
async def test_prepare_operates_without_answer_generation() -> None:
    generator = GeneratorDouble()
    coordinator = RAGCoordinator(
        options=RAGOptions(strategy="naive", top_k=3),
        strategies=StrategyRegistry((StrategyDouble(),)),
        generator=generator,
    )

    prepared = await coordinator.prepare("question")

    assert prepared.chunks
    assert prepared.context
    assert generator.context == ""
