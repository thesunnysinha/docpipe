"""Structural interface for document chunking plugins.

The protocol uses LangChain-style document objects but does not prescribe
chunking strategy, option names, chunk-size semantics, or metadata policy;
those are implementation-specific and should be documented by each chunker.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BaseChunker(Protocol):
    """Contract for synchronous and asynchronous document splitters.

    Both methods accept a list of document-like values and return chunk values
    compatible with the consuming pipeline. Implementations should preserve
    source metadata when their underlying splitting strategy supports it.
    """

    name: str

    def split_documents(self, documents: list[Any], **kwargs: Any) -> list[Any]:
        """Split input documents synchronously into pipeline-ready chunks.

        Args:
            documents: LangChain ``Document`` instances supplied by the
                pipeline.
            **kwargs: Chunker-specific controls such as size or overlap; their
                meaning and accepted names are implementation-defined.

        Returns:
            Chunk objects accepted by downstream ingestion. Ordering and
            metadata behavior depend on the chunker implementation.
        """
        ...

    async def asplit_documents(self, documents: list[Any], **kwargs: Any) -> list[Any]:
        """Split input documents asynchronously into pipeline-ready chunks.

        Args:
            documents: LangChain ``Document`` instances supplied by the
                pipeline.
            **kwargs: Chunker-specific controls; accepted names and semantics
                are implementation-defined.

        Returns:
            Chunk objects accepted by downstream ingestion.
        """
        ...

    @classmethod
    def is_available(cls) -> bool:
        """Report whether this chunker's required runtime dependencies are usable.

        Returns:
            ``True`` when the implementation considers its chunking backend
            available; input validity is checked only when splitting.
        """
        ...
