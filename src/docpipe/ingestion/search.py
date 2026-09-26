"""Vendor-neutral similarity search over the selected vector reader."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from docpipe.core.errors import ConfigurationError
from docpipe.embeddings.contracts import EmbeddingEncoder
from docpipe.plugins.contracts.vectorstore import (
    And,
    CollectionRef,
    Equals,
    FilterExpression,
    VectorCapability,
    VectorMatch,
    VectorQuery,
    VectorReader,
)
from docpipe.plugins.errors import PluginCapabilityError


@dataclass(frozen=True, slots=True)
class SearchCoordinator:
    """Encode a query and search without exposing a backend implementation."""

    reader: VectorReader
    encoder: EmbeddingEncoder
    collection: CollectionRef
    capabilities: frozenset[VectorCapability]

    async def search(
        self,
        text: str,
        *,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> tuple[VectorMatch, ...]:
        """Run one capability-checked dense search with typed metadata filters."""
        if VectorCapability.DENSE_SEARCH not in self.capabilities:
            raise PluginCapabilityError(
                "Selected vector plugin does not support dense search",
                context={"required_capability": VectorCapability.DENSE_SEARCH.value},
            )
        typed_filter = _typed_filters(filters or {})
        if typed_filter is not None and VectorCapability.METADATA_FILTER not in self.capabilities:
            raise PluginCapabilityError(
                "Selected vector plugin does not support metadata filtering",
                context={"required_capability": VectorCapability.METADATA_FILTER.value},
            )
        vector = await self.encoder.encode_query(text)
        return await self.reader.search(
            VectorQuery(
                collection=self.collection,
                dense_vector=vector,
                filter=typed_filter,
                limit=limit,
            )
        )


def _typed_filters(values: dict[str, Any]) -> FilterExpression | None:
    """Translate the legacy equality map at the API boundary."""
    if not values:
        return None
    try:
        expressions = tuple(Equals(key, value) for key, value in values.items())
    except (TypeError, ValueError) as error:
        raise ConfigurationError("filters must contain safe scalar field/value pairs") from error
    return expressions[0] if len(expressions) == 1 else And(expressions)
