"""semchunk hierarchical chunker."""

from __future__ import annotations

import asyncio
from typing import Any

from docpipe.core.errors import ConfigurationError
from docpipe.core.types import IngestionConfig


class SemchunkChunker:
    """Split document text with semchunk's hierarchical chunking utility.

    The adapter's length function counts whitespace-separated words, and the
    configured ``chunk_size`` is passed as the semchunk chunk size. This
    adapter does not set overlap.
    """

    name = "semchunk"
    license = "MIT"
    requires_gpu = False

    def __init__(self, config: IngestionConfig, **kwargs: Any) -> None:
        """Store ingestion settings after validating the optional dependency.

        Raises:
            ConfigurationError: If the optional ``semchunk`` package is absent.
        """
        if not self.is_available():
            raise ConfigurationError(
                "semchunk is not installed. Install with: pip install docpipe-sdk[semchunk]"
            )
        self._config = config

    def split_documents(self, documents: list[Any], **kwargs: Any) -> list[Any]:
        """Split each document's ``page_content`` and copy its metadata.

        Output chunks use the same class as their source document. Input and
        chunk order are preserved; no page identifiers or additional metadata
        are synthesized by this adapter.
        """
        import semchunk

        chunker = semchunk.chunkerify(
            lambda text: len(text.split()),
            self._config.chunk_size,
        )
        out: list[Any] = []
        for doc in documents:
            text = doc.page_content
            for piece in chunker(text):
                out.append(
                    doc.__class__(
                        page_content=piece,
                        metadata=dict(doc.metadata),
                    )
                )
        return out

    async def asplit_documents(self, documents: list[Any], **kwargs: Any) -> list[Any]:
        """Run :meth:`split_documents` in a worker thread."""
        return await asyncio.to_thread(self.split_documents, documents, **kwargs)

    @classmethod
    def is_available(cls) -> bool:
        """Return whether the optional top-level ``semchunk`` package imports."""
        try:
            import semchunk  # noqa: F401

            return True
        except ImportError:
            return False
