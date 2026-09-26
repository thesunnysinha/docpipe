"""Bounded Qdrant source aggregation over paged payload scans."""

from __future__ import annotations

from collections import Counter

from qdrant_client import AsyncQdrantClient

from docpipe.plugins.contracts.vectorstore import CollectionRef, SourceAggregate
from docpipe.plugins.errors import VectorStoreOperationError
from docpipe.vectorstores.qdrant.operations import QdrantOperations


async def aggregate_sources(
    client: AsyncQdrantClient,
    collection: CollectionRef,
    *,
    max_scan_points: int,
    operations: QdrantOperations,
) -> tuple[SourceAggregate, ...]:
    """Count source IDs only when every page fits the configured scan limit."""
    counts: Counter[str] = Counter()
    scanned = 0
    offset = None
    while True:
        page_size = min(256, max_scan_points - scanned)
        if page_size < 1:
            raise VectorStoreOperationError(
                "Qdrant source aggregation exceeded configured scan limit",
                context={"provider": "qdrant", "operation": "aggregate_sources"},
            )
        points, offset = await operations.execute(
            "vectorstore.aggregate.sources",
            client.scroll(
                collection_name=collection.name,
                offset=offset,
                limit=page_size,
                with_payload=["source_id"],
                with_vectors=False,
            ),
        )
        scanned += len(points)
        for point in points:
            source = (point.payload or {}).get("source_id")
            if isinstance(source, str) and source:
                counts[source] += 1
        if offset is None:
            break
    return tuple(
        SourceAggregate(source_id=source, record_count=count)
        for source, count in sorted(counts.items())
    )
