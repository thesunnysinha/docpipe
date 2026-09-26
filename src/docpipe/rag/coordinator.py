"""Vendor-neutral orchestration for retrieval, reranking, and generation."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from docpipe.core.types import RAGChunk, RAGResult
from docpipe.rag.generation import AnswerGenerator, build_context
from docpipe.rag.retrieval.registry import StrategyRegistry

logger = logging.getLogger(__name__)


class AsyncReranker(Protocol):
    """Score and order retrieved chunks without vendor-specific values."""

    async def rerank(
        self,
        question: str,
        chunks: tuple[RAGChunk, ...],
        *,
        top_n: int,
    ) -> tuple[RAGChunk, ...]:
        """Return at most ``top_n`` chunks in relevance order."""
        ...


@dataclass(frozen=True, slots=True)
class RAGOptions:
    """Runtime controls used by the RAG coordinator."""

    strategy: str
    top_k: int = 5
    max_chunks_per_source: int = 2
    rerank_top_n: int | None = None

    def __post_init__(self) -> None:
        if self.top_k < 1:
            raise ValueError("top_k must be at least one")
        if self.max_chunks_per_source < 0:
            raise ValueError("max_chunks_per_source cannot be negative")
        if self.rerank_top_n is not None and self.rerank_top_n < 1:
            raise ValueError("rerank_top_n must be at least one")


@dataclass(frozen=True, slots=True)
class PreparedQuery:
    """Retrieved and formatted context ready for answer generation."""

    chunks: tuple[RAGChunk, ...]
    context: str
    metadata: Mapping[str, object] = field(default_factory=dict)


class RAGCoordinator:
    """Sequence RAG components while keeping vendor policy at composition roots."""

    def __init__(
        self,
        *,
        options: RAGOptions,
        strategies: StrategyRegistry,
        generator: AnswerGenerator,
        reranker: AsyncReranker | None = None,
    ) -> None:
        self._options = options
        self._strategies = strategies
        self._generator = generator
        self._reranker = reranker

    async def prepare(self, question: str) -> PreparedQuery:
        """Retrieve, optionally rerank, and cap chunks without generating an answer."""
        strategy = self._strategies.require(self._options.strategy)
        retrieved = await strategy.retrieve(question)
        chunks = retrieved.chunks
        logger.info(
            "rag.retrieval.completed",
            extra={
                "event": "rag.retrieval.completed",
                "strategy": self._options.strategy,
                "chunk_count": len(chunks),
            },
        )
        if self._reranker is not None:
            top_n = self._options.rerank_top_n or self._options.top_k
            chunks = await self._reranker.rerank(question, chunks, top_n=top_n)
            logger.info(
                "rag.rerank.completed",
                extra={"event": "rag.rerank.completed", "chunk_count": len(chunks)},
            )
        chunks = _cap_by_source(chunks, self._options.max_chunks_per_source)
        chunks = chunks[: self._options.top_k]
        return PreparedQuery(chunks, build_context(chunks), retrieved.metadata)

    async def query(self, question: str) -> RAGResult:
        """Run retrieval and generation, returning the stable public result model."""
        started = time.perf_counter()
        logger.info(
            "rag.query.started",
            extra={"event": "rag.query.started", "strategy": self._options.strategy},
        )
        try:
            prepared = await self.prepare(question)
            generated = await self._generator.generate(question, prepared.context)
        except BaseException as error:
            logger.warning(
                "rag.query.failed",
                extra={"event": "rag.query.failed", "error_type": type(error).__name__},
            )
            raise
        logger.info(
            "rag.generation.completed",
            extra={"event": "rag.generation.completed", "has_usage": generated.usage is not None},
        )
        sources = list(dict.fromkeys(chunk.source for chunk in prepared.chunks))
        return RAGResult(
            query=question,
            answer=generated.answer,
            strategy=self._options.strategy,
            chunks=list(prepared.chunks),
            sources=sources,
            timing_seconds=time.perf_counter() - started,
            usage=generated.usage,
            structured=generated.structured,
            metadata=dict(prepared.metadata),
        )


def _cap_by_source(chunks: tuple[RAGChunk, ...], max_per_source: int) -> tuple[RAGChunk, ...]:
    if max_per_source == 0:
        return chunks
    counts: dict[str, int] = {}
    selected: list[RAGChunk] = []
    for chunk in chunks:
        count = counts.get(chunk.source, 0)
        if count >= max_per_source:
            continue
        selected.append(chunk)
        counts[chunk.source] = count + 1
    return tuple(selected)
