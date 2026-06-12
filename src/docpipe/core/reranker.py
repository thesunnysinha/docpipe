"""BaseReranker protocol for retrieval reranking plugins."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from docpipe.core.types import RAGChunk


@runtime_checkable
class BaseReranker(Protocol):
    """Protocol that all rerankers must implement."""

    name: str

    def rerank(self, query: str, chunks: list[RAGChunk], *, top_n: int) -> list[RAGChunk]:
        """Rerank chunks by relevance to the query."""
        ...

    @classmethod
    def is_available(cls) -> bool:
        """Return True if dependencies are installed."""
        ...
