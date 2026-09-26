"""Vendor-neutral embedding encoder port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingEncoder(Protocol):
    """Encode text into plain immutable floating-point vectors."""

    async def encode_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Encode document texts in input order."""
        ...

    async def encode_query(self, text: str) -> tuple[float, ...]:
        """Encode one search query."""
        ...
