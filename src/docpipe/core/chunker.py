"""BaseChunker protocol for document chunking plugins."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BaseChunker(Protocol):
    """Protocol that all chunkers must implement."""

    name: str

    def split_documents(self, documents: list[Any], **kwargs: Any) -> list[Any]:
        """Split LangChain Document objects into chunks."""
        ...

    async def asplit_documents(self, documents: list[Any], **kwargs: Any) -> list[Any]:
        """Async variant."""
        ...

    @classmethod
    def is_available(cls) -> bool:
        """Return True if dependencies are installed."""
        ...
