"""BGE cross-encoder reranker."""

from __future__ import annotations

from typing import Any

from docpipe.core.errors import ConfigurationError, RAGError
from docpipe.core.types import RAGChunk


class BGEReranker:
    """Rerank candidate chunks with a local SentenceTransformers cross-encoder.

    The optional dependency is checked at construction, while the model itself
    is loaded on first non-empty rerank. Model files may be downloaded and are
    cached by the underlying library; configure the Docpipe model cache setting
    to control its cache directory.
    """

    name = "bge"
    license = "MIT"
    requires_gpu = False

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        """Configure a model identifier without loading model weights.

        Raises:
            ConfigurationError: If ``sentence-transformers`` is unavailable.
        """
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
        """Return up to ``top_n`` input chunks ordered by cross-encoder score.

        An empty candidate list returns immediately without loading the model.
        Scores are used only for ordering and are not written back to chunks.

        Raises:
            RAGError: If model prediction fails.
        """
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
        """Return whether the optional SentenceTransformers package can import."""
        try:
            import sentence_transformers  # noqa: F401

            return True
        except ImportError:
            return False
