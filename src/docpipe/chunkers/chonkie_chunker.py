"""Chonkie semantic and late chunkers."""

from __future__ import annotations

import asyncio
from typing import Any

from docpipe.core.errors import ConfigurationError
from docpipe.core.types import IngestionConfig


class _ChonkieBase:
    license = "MIT"
    requires_gpu = False

    def __init__(self, config: IngestionConfig, **kwargs: Any) -> None:
        if not self.is_available():
            raise ConfigurationError(
                "Chonkie is not installed. Install with: pip install docpipe-sdk[chonkie]"
            )
        self._config = config
        self._chunker = self._build_chunker(config, **kwargs)

    def _build_chunker(self, config: IngestionConfig, **kwargs: Any) -> Any:
        raise NotImplementedError

    def split_documents(self, documents: list[Any], **kwargs: Any) -> list[Any]:
        out: list[Any] = []
        for doc in documents:
            chunks = self._chunker(doc.page_content)
            for chunk in chunks:
                text = chunk.text if hasattr(chunk, "text") else str(chunk)
                out.append(
                    doc.__class__(
                        page_content=text,
                        metadata=dict(doc.metadata),
                    )
                )
        return out

    async def asplit_documents(self, documents: list[Any], **kwargs: Any) -> list[Any]:
        return await asyncio.to_thread(self.split_documents, documents, **kwargs)

    @classmethod
    def is_available(cls) -> bool:
        try:
            import chonkie  # noqa: F401

            return True
        except ImportError:
            return False


class ChonkieSemanticChunker(_ChonkieBase):
    name = "chonkie-semantic"

    def _build_chunker(self, config: IngestionConfig, **kwargs: Any) -> Any:
        from chonkie import SemanticChunker

        model = kwargs.get("embedding_model") or config.embedding_model
        return SemanticChunker(
            embedding_model=model,
            chunk_size=config.chunk_size,
        )


class ChonkieLateChunker(_ChonkieBase):
    name = "chonkie-late"

    def _build_chunker(self, config: IngestionConfig, **kwargs: Any) -> Any:
        from chonkie import LateChunker

        model = kwargs.get("embedding_model") or config.embedding_model
        return LateChunker(
            embedding_model=model,
            chunk_size=config.chunk_size,
        )
