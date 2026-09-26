"""Optional Chonkie-backed semantic and late chunker adapters."""

from __future__ import annotations

import asyncio
from typing import Any

from docpipe.core.errors import ConfigurationError
from docpipe.core.types import IngestionConfig


class _ChonkieBase:
    """Shared adapter behavior for Chonkie chunkers.

    Subclasses select a Chonkie implementation in ``_build_chunker``. Each
    generated chunk is returned using the input document's class, with a copy
    of its metadata.
    """

    license = "MIT"
    requires_gpu = False

    def __init__(self, config: IngestionConfig, **kwargs: Any) -> None:
        """Build the configured Chonkie chunker.

        Raises:
            ConfigurationError: If the optional ``chonkie`` package is absent.
        """
        if not self.is_available():
            raise ConfigurationError(
                "Chonkie is not installed. Install with: pip install docpipe-sdk[chonkie]"
            )
        self._config = config
        self._chunker = self._build_chunker(config, **kwargs)

    def _build_chunker(self, config: IngestionConfig, **kwargs: Any) -> Any:
        """Construct the backend chunker; implemented by each concrete adapter."""
        raise NotImplementedError

    def split_documents(self, documents: list[Any], **kwargs: Any) -> list[Any]:
        """Split document-like inputs and preserve their class and metadata.

        Each input's ``page_content`` is sent to the configured Chonkie
        chunker. Chunk objects with a ``text`` attribute use that value;
        other values are converted to strings. Input order and chunk order are
        preserved.
        """
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
        """Run :meth:`split_documents` in a worker thread."""
        return await asyncio.to_thread(self.split_documents, documents, **kwargs)

    @classmethod
    def is_available(cls) -> bool:
        """Return whether the optional top-level ``chonkie`` package imports."""
        try:
            import chonkie  # noqa: F401

            return True
        except ImportError:
            return False


class ChonkieSemanticChunker(_ChonkieBase):
    """Chunk by semantic similarity using Chonkie's semantic chunker."""

    name = "chonkie-semantic"

    def _build_chunker(self, config: IngestionConfig, **kwargs: Any) -> Any:
        """Build Chonkie's semantic chunker from the configured model and size."""
        from chonkie import SemanticChunker

        model = kwargs.get("embedding_model") or config.embedding_model
        return SemanticChunker(
            embedding_model=model,
            chunk_size=config.chunk_size,
        )


class ChonkieLateChunker(_ChonkieBase):
    """Use Chonkie's late-chunking strategy for configured embeddings."""

    name = "chonkie-late"

    def _build_chunker(self, config: IngestionConfig, **kwargs: Any) -> Any:
        """Build Chonkie's late chunker from the configured model and size."""
        from chonkie import LateChunker

        model = kwargs.get("embedding_model") or config.embedding_model
        return LateChunker(
            embedding_model=model,
            chunk_size=config.chunk_size,
        )
