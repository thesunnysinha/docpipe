"""Adapter from LangChain-style embedding objects to plain vectors."""

from __future__ import annotations

from typing import Protocol

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.contracts.vectorstore.values import normalize_vector


class LangChainEmbeddingsLike(Protocol):
    """Narrow structural surface used from a LangChain embedding object."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple document texts."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Encode one query text."""
        ...


class LangChainEmbeddingAdapter:
    """Keep LangChain objects behind the internal embedding port."""

    def __init__(
        self,
        embeddings: LangChainEmbeddingsLike,
        blocking_runner: BoundedBlockingRunner,
    ) -> None:
        self._embeddings = embeddings
        self._blocking_runner = blocking_runner

    async def encode_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Encode documents using bounded blocking execution."""
        vectors = await self._blocking_runner.run(self._embeddings.embed_documents, list(texts))
        if len(vectors) != len(texts):
            raise ValueError("embedding provider returned an unexpected document count")
        return tuple(normalize_vector(vector, field_name="embedding") for vector in vectors)

    async def encode_query(self, text: str) -> tuple[float, ...]:
        """Encode a query using bounded blocking execution."""
        vector = await self._blocking_runner.run(self._embeddings.embed_query, text)
        return normalize_vector(vector, field_name="embedding")
