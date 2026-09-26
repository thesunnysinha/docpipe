"""Cohere API reranker."""

from __future__ import annotations

from typing import Any

from docpipe.core.errors import RAGError
from docpipe.core.types import RAGChunk


class CohereReranker:
    """Rerank candidates through Cohere's hosted reranking API.

    The ``cohere`` SDK is optional and imported when reranking begins. Client
    authentication and network configuration are read by the SDK from its
    normal operator-managed environment/configuration.
    """

    name = "cohere"
    license = "MIT"
    requires_gpu = False

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        """Select a Cohere rerank model; no request is made during setup."""
        self._model = model or "rerank-english-v3.0"

    def rerank(self, query: str, chunks: list[RAGChunk], *, top_n: int) -> list[RAGChunk]:
        """Return the provider-ranked candidates, limited by ``top_n``.

        Chunk content is sent to Cohere as the reranking input. The provider
        response determines the selected order; SDK, authentication, and
        network exceptions propagate without being normalized here. Install
        the optional ``cohere`` package to use this adapter.
        """
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
        """Return whether the optional Cohere SDK can import."""
        try:
            import cohere  # noqa: F401

            return True
        except ImportError:
            return False
