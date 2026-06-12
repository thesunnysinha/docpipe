"""FlashRank lightweight reranker."""

from __future__ import annotations

from typing import Any

from docpipe.core.errors import RAGError
from docpipe.core.types import RAGChunk


class FlashRankReranker:
    name = "flashrank"
    license = "MIT"
    requires_gpu = False

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        self._model = model or "ms-marco-MiniLM-L-12-v2"

    def rerank(self, query: str, chunks: list[RAGChunk], *, top_n: int) -> list[RAGChunk]:
        try:
            from flashrank import Ranker as FlashRanker
            from flashrank import RerankRequest
        except ImportError as err:
            raise RAGError(
                "flashrank reranker requires the 'flashrank' package. "
                "Install with: pip install 'docpipe-sdk[rerank]'"
            ) from err
        ranker = FlashRanker(model_name=self._model)
        request = RerankRequest(query=query, passages=[{"text": c.content} for c in chunks])
        results = ranker.rerank(request)
        reranked = [chunks[r["index"]] for r in results]
        return reranked[:top_n]

    @classmethod
    def is_available(cls) -> bool:
        try:
            import flashrank  # noqa: F401

            return True
        except ImportError:
            return False
