"""semchunk hierarchical chunker."""

from __future__ import annotations

import asyncio
from typing import Any

from docpipe.core.errors import ConfigurationError
from docpipe.core.types import IngestionConfig


class SemchunkChunker:
    """Hierarchical structural chunking via semchunk."""

    name = "semchunk"
    license = "MIT"
    requires_gpu = False

    def __init__(self, config: IngestionConfig, **kwargs: Any) -> None:
        if not self.is_available():
            raise ConfigurationError(
                "semchunk is not installed. Install with: pip install docpipe-sdk[semchunk]"
            )
        self._config = config

    def split_documents(self, documents: list[Any], **kwargs: Any) -> list[Any]:
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
        return await asyncio.to_thread(self.split_documents, documents, **kwargs)

    @classmethod
    def is_available(cls) -> bool:
        try:
            import semchunk  # noqa: F401

            return True
        except ImportError:
            return False
