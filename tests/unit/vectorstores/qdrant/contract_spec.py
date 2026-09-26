"""Real Qdrant local mode exercises the public vector conformance suite."""

from __future__ import annotations

import pytest

pytest.importorskip("qdrant_client")

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    Equals,
    VectorQuery,
    VectorRecord,
    WriteBatch,
)
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.testing import assert_vector_store_conformance
from docpipe.vectorstores.qdrant.factory import create_plugin


@pytest.mark.asyncio
async def should_conform_locally_and_support_filtered_search() -> None:
    plugin = create_plugin(
        PluginConfig(provider="qdrant", options={"location": ":memory:", "collection": "contract"}),
        context=PluginFactoryContext(blocking_runner=BoundedBlockingRunner(1)),
    )
    async with plugin:
        await assert_vector_store_conformance(
            plugin.binding, collection=CollectionRef("contract"), dimensions=3
        )
        await plugin.ensure_collection(CollectionRef("contract"), 3)
        await plugin.upsert(
            WriteBatch(
                CollectionRef("contract"),
                (
                    VectorRecord(
                        record_id="stable-id",
                        text="report",
                        vector=(1.0, 0.0, 0.0),
                        metadata={"kind": "report"},
                        source_id="s3://bucket/report.pdf",
                    ),
                ),
            )
        )
        matches = await plugin.search(
            VectorQuery(
                collection=CollectionRef("contract"),
                dense_vector=(1.0, 0.0, 0.0),
                filter=Equals("kind", "report"),
                limit=5,
            )
        )
        assert matches[0].record_id == "stable-id"
        assert matches[0].source_id == "s3://bucket/report.pdf"
        aggregates = await plugin.aggregate_sources(CollectionRef("contract"))
        assert aggregates[0].record_count == 1
        await plugin.upsert(
            WriteBatch(
                CollectionRef("contract"),
                (
                    VectorRecord(
                        record_id="stable-id",
                        text="report updated",
                        vector=(1.0, 0.0, 0.0),
                        source_id="s3://bucket/report.pdf",
                    ),
                ),
            )
        )
        aggregates = await plugin.aggregate_sources(CollectionRef("contract"))
        assert aggregates[0].record_count == 1
