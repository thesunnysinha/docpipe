"""Cohere API reranker."""

from __future__ import annotations

from typing import Any

from docpipe.core.errors import RAGError
from docpipe.core.types import RAGChunk


class CohereReranker:
    name = "cohere"
    license = "MIT"
    requires_gpu = False

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        self._model = model or "rerank-english-v3.0"

    def rerank(self, query: str, chunks: list[RAGChunk], *, top_n: int) -> list[RAGChunk]:
        try:
            import cohere
        except ImportError as err:
            raise RAGError(
                "cohere reranker requires the 'cohere' package. Install with: pip install cohere"
            ) from err
        co = cohere.Client()
        docs = [c.content for c in chunks]
        response = co.rerank(query=query, documents=docs, model=self._model, top_n=top_n)
        return [chunks[r.index] for r in response.results]

    @classmethod
    def is_available(cls) -> bool:
        try:
            import cohere  # noqa: F401

            return True
        except ImportError:
            return False
