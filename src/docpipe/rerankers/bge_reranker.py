"""BGE cross-encoder reranker."""

from __future__ import annotations

from typing import Any

from docpipe.core.errors import ConfigurationError, RAGError
from docpipe.core.types import RAGChunk


class BGEReranker:
    name = "bge"
    license = "MIT"
    requires_gpu = False

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        if not self.is_available():
            raise ConfigurationError(
                "BGE reranker requires sentence-transformers. "
                "Install with: pip install docpipe-sdk[rerank-quality]"
            )
        self._model = model or "BAAI/bge-reranker-v2-m3"
        self._cross_encoder: Any = None

    def _get_model(self) -> Any:
        if self._cross_encoder is None:
            from sentence_transformers import CrossEncoder

            from docpipe.config import get_settings

            settings = get_settings()
            kwargs: dict[str, Any] = {}
            if settings.model_cache_dir is not None:
                kwargs["cache_folder"] = str(settings.model_cache_dir)
            self._cross_encoder = CrossEncoder(self._model, **kwargs)
        return self._cross_encoder

    def rerank(self, query: str, chunks: list[RAGChunk], *, top_n: int) -> list[RAGChunk]:
        if not chunks:
            return []
        model = self._get_model()
        pairs = [[query, c.content] for c in chunks]
        try:
            scores = model.predict(pairs)
        except Exception as e:
            raise RAGError(f"BGE rerank failed: {e}") from e
        ranked = sorted(
            zip(scores, chunks, strict=True),
            key=lambda item: float(item[0]),
            reverse=True,
        )
        return [chunk for _, chunk in ranked[:top_n]]

    @classmethod
    def is_available(cls) -> bool:
        try:
            import sentence_transformers  # noqa: F401

            return True
        except ImportError:
            return False
