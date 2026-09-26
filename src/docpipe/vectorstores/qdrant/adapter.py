"""Qdrant facets over the asynchronous Qdrant client."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import AsyncQdrantClient, models

from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    SourceAggregate,
    VectorCapability,
    VectorMatch,
    VectorQuery,
    VectorStoreBinding,
    WriteBatch,
    WriteBatchResult,
)
from docpipe.plugins.errors import (
    PluginCapabilityError,
    VectorStoreOperationError,
)
from docpipe.vectorstores.qdrant.aggregation import aggregate_sources
from docpipe.vectorstores.qdrant.filters import compile_filter
from docpipe.vectorstores.qdrant.operations import QdrantOperations
from docpipe.vectorstores.qdrant.responses import validate_point_count
from docpipe.vectorstores.qdrant.schemas import QdrantConfig


class QdrantAdapter:
    """Operation-owned dense vector adapter with safe errors and bounded scans."""

    capabilities = frozenset(
        {
            VectorCapability.DENSE_SEARCH,
            VectorCapability.METADATA_FILTER,
            VectorCapability.SOURCE_AGGREGATION,
            VectorCapability.UPSERT,
            VectorCapability.DELETE_BY_SOURCE,
            VectorCapability.COLLECTION_ADMIN,
            VectorCapability.HEALTH,
        }
    )

    def __init__(self, config: QdrantConfig, client: AsyncQdrantClient) -> None:
        self._config = config
        self._client = client
        self._operations = QdrantOperations()

    @property
    def binding(self) -> VectorStoreBinding:
        """Advertise implemented facets without exposing the vendor client."""
        return VectorStoreBinding(
            capabilities=self.capabilities,
            reader=self,
            writer=self,
            admin=self,
            health=self,
        )

    async def __aenter__(self) -> QdrantAdapter:
        """Enter an operation-owned adapter instance."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Close the selected client's sockets and local resources."""
        await self._client.close()

    async def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None:
        """Create a dense collection, or verify an existing collection's width."""
        if dimensions < 1:
            raise ValueError("vector dimensions must be positive")
        exists = await self._operations.execute(
            "vectorstore.collection.exists",
            self._client.collection_exists(collection.name),
        )
        if exists:
            info = await self._operations.execute(
                "vectorstore.collection.inspect",
                self._client.get_collection(collection.name),
            )
            vectors = info.config.params.vectors
            if not isinstance(vectors, models.VectorParams) or vectors.size != dimensions:
                raise VectorStoreOperationError(
                    "Qdrant collection has incompatible vector dimensions",
                    context={"provider": "qdrant", "operation": "ensure_collection"},
                )
            return
        distance = {
            "cosine": models.Distance.COSINE,
            "dot": models.Distance.DOT,
            "euclid": models.Distance.EUCLID,
        }[self._config.distance]
        await self._operations.execute(
            "vectorstore.collection.create",
            self._client.create_collection(
                collection_name=collection.name,
                vectors_config=models.VectorParams(size=dimensions, distance=distance),
            ),
        )

    async def delete_collection(self, collection: CollectionRef) -> None:
        """Delete an entire collection through the admin facet."""
        await self._operations.execute(
            "vectorstore.collection.delete",
            self._client.delete_collection(collection.name),
        )

    async def upsert(self, batch: WriteBatch) -> WriteBatchResult:
        """Upsert deterministic UUID points and account for uncertain writes."""
        points = [
            models.PointStruct(
                id=str(uuid5(NAMESPACE_URL, record.record_id)),
                vector=cast(list[float], list(record.vector)),
                payload={
                    "record_id": record.record_id,
                    "text": record.text,
                    "metadata": _thaw(record.metadata),
                    "source_id": record.source_id,
                },
            )
            for record in batch.records
        ]
        result = await self._operations.execute(
            "vectorstore.upsert",
            self._client.upsert(collection_name=batch.collection.name, points=points, wait=True),
        )
        completed = result.status == models.UpdateStatus.COMPLETED
        return WriteBatchResult(
            requested=len(points),
            accepted=len(points) if completed else 0,
            uncertain=0 if completed else len(points),
        )

    async def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]:
        """Run a dense query with typed metadata filters."""
        if query.dense_vector is None or query.sparse_vector is not None:
            raise PluginCapabilityError(
                "Qdrant adapter supports dense queries only",
                plugin="qdrant",
                context={"required_capability": VectorCapability.DENSE_SEARCH.value},
            )
        result = await self._operations.execute(
            "vectorstore.search",
            self._client.query_points(
                collection_name=query.collection.name,
                query=cast(list[float], list(query.dense_vector)),
                query_filter=compile_filter(query.filter) if query.filter is not None else None,
                limit=query.limit,
                with_payload=True,
            ),
        )
        matches: list[VectorMatch] = []
        for point in result.points:
            payload = point.payload or {}
            metadata = payload.get("metadata")
            matches.append(
                VectorMatch(
                    record_id=str(payload.get("record_id", point.id)),
                    score=float(point.score),
                    text=str(payload.get("text", "")),
                    metadata=metadata if isinstance(metadata, dict) else {},
                    source_id=payload.get("source_id")
                    if isinstance(payload.get("source_id"), str)
                    else None,
                )
            )
        return tuple(matches)

    async def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        """Delete exact source matches, waiting for the Qdrant update result."""
        source_filter = models.Filter(
            must=[models.FieldCondition(key="source_id", match=models.MatchValue(value=source_id))]
        )
        before = await self._operations.execute(
            "vectorstore.delete.count",
            self._client.count(
                collection_name=collection.name, count_filter=source_filter, exact=True
            ),
        )
        result = await self._operations.execute(
            "vectorstore.delete",
            self._client.delete(
                collection_name=collection.name,
                points_selector=models.FilterSelector(filter=source_filter),
                wait=True,
            ),
        )
        if result.status != models.UpdateStatus.COMPLETED:
            raise VectorStoreOperationError(
                "Qdrant deletion outcome is uncertain",
                context={"provider": "qdrant", "operation": "delete_by_source"},
            )
        return validate_point_count(before.count)

    async def aggregate_sources(self, collection: CollectionRef) -> tuple[SourceAggregate, ...]:
        """Page through source payloads with a strict scan limit."""
        return await aggregate_sources(
            self._client,
            collection,
            max_scan_points=self._config.max_scan_points,
            operations=self._operations,
        )

    async def health(self) -> bool:
        """Check the selected Qdrant endpoint without returning endpoint details."""
        await self._operations.execute("vectorstore.health", self._client.get_collections())
        return True


def _thaw(value: object) -> object:
    """Convert immutable domain metadata to vendor JSON containers."""
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value
