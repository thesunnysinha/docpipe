"""Shared contracts and vector-search mechanics for retrieval strategies."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol

from docpipe.core.types import RAGChunk
from docpipe.embeddings.contracts import EmbeddingEncoder
from docpipe.plugins.contracts.vectorstore import (
    And,
    CollectionRef,
    FilterExpression,
    VectorCapability,
    VectorMatch,
    VectorQuery,
    VectorReader,
)
from docpipe.plugins.errors import PluginCapabilityError

_TOKEN_PATTERN = re.compile(r"[\w]+", re.UNICODE)
_SPARSE_DIMENSIONS = 1 << 20


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Immutable chunks and non-sensitive strategy metadata."""

    chunks: tuple[RAGChunk, ...]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "chunks", tuple(self.chunks))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


class RetrievalStrategy(Protocol):
    """Common asynchronous contract implemented by every retrieval strategy."""

    @property
    def name(self) -> str:
        """Return the strategy's stable registry key."""
        ...

    async def retrieve(self, question: str) -> RetrievalResult:
        """Retrieve relevant chunks for one question."""
        ...


class TextRewriter(Protocol):
    """Minimal text-generation port used by query rewriting strategies."""

    async def complete(self, prompt: str) -> str:
        """Return a textual completion for a fully rendered prompt."""
        ...


@dataclass(frozen=True, slots=True)
class VectorSearch:
    """Capability-aware adapter over vector reader and embedding ports."""

    reader: VectorReader
    encoder: EmbeddingEncoder
    collection: CollectionRef | str
    capabilities: frozenset[VectorCapability]
    limit: int
    default_filter: FilterExpression | None = None

    def __post_init__(self) -> None:
        collection = (
            CollectionRef(self.collection) if isinstance(self.collection, str) else self.collection
        )
        object.__setattr__(self, "collection", collection)
        if self.limit < 1:
            raise ValueError("retrieval limit must be at least one")

    async def dense(
        self,
        text: str,
        *,
        filter: FilterExpression | None = None,
        limit: int | None = None,
    ) -> tuple[RAGChunk, ...]:
        """Run a dense search after negotiating required capabilities."""
        self._require(VectorCapability.DENSE_SEARCH, "dense search")
        effective_filter = _combine_filters(self.default_filter, filter)
        if effective_filter is not None:
            self._require(VectorCapability.METADATA_FILTER, "metadata filtering")
        vector = await self.encoder.encode_query(text)
        return await self._execute(
            VectorQuery(
                collection=self._collection,
                dense_vector=vector,
                filter=effective_filter,
                limit=limit or self.limit,
            )
        )

    async def hybrid(self, text: str) -> tuple[RAGChunk, ...]:
        """Run a native hybrid search using deterministic sparse features."""
        self._require(VectorCapability.HYBRID_SEARCH, "hybrid search")
        if self.default_filter is not None:
            self._require(VectorCapability.METADATA_FILTER, "metadata filtering")
        vector = await self.encoder.encode_query(text)
        return await self._execute(
            VectorQuery(
                collection=self._collection,
                dense_vector=vector,
                sparse_vector=_sparse_vector(text),
                filter=self.default_filter,
                limit=self.limit,
            )
        )

    @property
    def _collection(self) -> CollectionRef:
        collection = self.collection
        assert isinstance(collection, CollectionRef)
        return collection

    def _require(self, capability: VectorCapability, operation: str) -> None:
        if capability not in self.capabilities:
            raise PluginCapabilityError(
                f"Selected vector plugin does not support {operation}",
                context={"required_capability": capability.value},
            )

    async def _execute(self, query: VectorQuery) -> tuple[RAGChunk, ...]:
        matches = await self.reader.search(query)
        return tuple(_match_to_chunk(match) for match in matches)


def _match_to_chunk(match: VectorMatch) -> RAGChunk:
    metadata = dict(match.metadata)
    source = match.source_id or str(metadata.get("source", "unknown"))
    page_value = metadata.get("page")
    page = page_value if isinstance(page_value, int) and not isinstance(page_value, bool) else None
    return RAGChunk(
        content=match.text,
        score=match.score,
        source=source,
        page=page,
        metadata=metadata,
    )


def _sparse_vector(text: str) -> Mapping[int, float]:
    counts: dict[int, float] = {}
    for token in _TOKEN_PATTERN.findall(text.casefold()):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest, "big") % _SPARSE_DIMENSIONS
        counts[index] = counts.get(index, 0.0) + 1.0
    if not counts:
        counts[0] = 1.0
    return counts


def _combine_filters(
    default: FilterExpression | None, override: FilterExpression | None
) -> FilterExpression | None:
    if default is None:
        return override
    if override is None:
        return default
    return And((default, override))
