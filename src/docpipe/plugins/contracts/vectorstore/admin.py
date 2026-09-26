"""Vector collection administration facet."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from docpipe.plugins.contracts.vectorstore.models import CollectionRef


@runtime_checkable
class VectorCollectionAdmin(Protocol):
    """Create and remove logical vector collections."""

    async def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None:
        """Ensure a compatible collection exists."""
        ...

    async def delete_collection(self, collection: CollectionRef) -> None:
        """Remove a collection and its records."""
        ...
