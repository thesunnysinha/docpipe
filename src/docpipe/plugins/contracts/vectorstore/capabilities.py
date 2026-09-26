"""Versioned vector capabilities and facet binding metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from docpipe.plugins.contracts.vectorstore.admin import VectorCollectionAdmin
from docpipe.plugins.contracts.vectorstore.reader import VectorReader
from docpipe.plugins.contracts.vectorstore.writer import VectorWriter


class VectorCapability(str, Enum):
    """Versioned vector-store behavior that callers may negotiate."""

    DENSE_SEARCH = "dense-search.v1"
    SPARSE_SEARCH = "sparse-search.v1"
    HYBRID_SEARCH = "hybrid-search.v1"
    METADATA_FILTER = "metadata-filter.v1"
    SOURCE_AGGREGATION = "source-aggregation.v1"
    UPSERT = "upsert.v1"
    DELETE_BY_SOURCE = "delete-by-source.v1"
    COLLECTION_ADMIN = "collection-admin.v1"
    HEALTH = "health.v1"


@runtime_checkable
class PluginHealthProbe(Protocol):
    """Minimal availability check shared by plugin categories."""

    async def health(self) -> bool:
        """Return whether the configured dependency is usable."""
        ...


@dataclass(frozen=True, slots=True)
class VectorStoreBinding:
    """Typed group of optional facets and their advertised capabilities."""

    capabilities: frozenset[VectorCapability]
    reader: VectorReader | None = None
    writer: VectorWriter | None = None
    admin: VectorCollectionAdmin | None = None
    health: PluginHealthProbe | None = None

    def __post_init__(self) -> None:
        """Ensure every advertised behavior has an implementation facet."""
        reader_capabilities = {
            VectorCapability.DENSE_SEARCH,
            VectorCapability.SPARSE_SEARCH,
            VectorCapability.HYBRID_SEARCH,
            VectorCapability.METADATA_FILTER,
            VectorCapability.SOURCE_AGGREGATION,
        }
        writer_capabilities = {VectorCapability.UPSERT, VectorCapability.DELETE_BY_SOURCE}
        if self.capabilities & reader_capabilities and self.reader is None:
            raise ValueError("vector reader facet is required by advertised capabilities")
        if self.capabilities & writer_capabilities and self.writer is None:
            raise ValueError("vector writer facet is required by advertised capabilities")
        if VectorCapability.COLLECTION_ADMIN in self.capabilities and self.admin is None:
            raise ValueError("vector admin facet is required by advertised capabilities")
        if VectorCapability.HEALTH in self.capabilities and self.health is None:
            raise ValueError("health facet is required by advertised capabilities")
