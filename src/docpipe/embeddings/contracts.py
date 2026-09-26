"""Vendor-neutral embedding encoder port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingEncoder(Protocol):
    """Encode text into plain immutable floating-point vectors.

    Implementations preserve document input order and return one vector per
    input. Provider failures propagate through the async methods; callers should
    validate dimensions against the selected vector collection before writing.
    """

    async def encode_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Return one normalized vector for each document, in input order."""
        ...

    async def encode_query(self, text: str) -> tuple[float, ...]:
        """Return one normalized vector suitable for query search."""
        ...
