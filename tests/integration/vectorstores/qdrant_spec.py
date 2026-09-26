"""Qdrant conformance against an explicitly configured ephemeral server."""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest

pytest.importorskip("qdrant_client")

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.contracts.vectorstore import CollectionRef
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.testing import assert_vector_store_conformance
from docpipe.vectorstores.qdrant.factory import create_plugin


@pytest.mark.asyncio
async def should_conform_against_qdrant_server() -> None:
    url = os.getenv("DOCPIPE_TEST_QDRANT_URL")
    if not url:
        pytest.skip("DOCPIPE_TEST_QDRANT_URL is not configured")
    collection = CollectionRef(f"contract_{uuid4().hex[:12]}")
    plugin = create_plugin(
        PluginConfig(
            provider="qdrant",
            options={"url": url, "allow_insecure_http": url.startswith("http://")},
        ),
        context=PluginFactoryContext(blocking_runner=BoundedBlockingRunner(1)),
    )
    async with plugin:
        for attempt in range(20):
            try:
                await plugin.health()
                break
            except Exception:
                if attempt == 19:
                    raise
                await asyncio.sleep(0.5)
        try:
            await assert_vector_store_conformance(
                plugin.binding, collection=collection, dimensions=8
            )
        finally:
            await plugin.delete_collection(collection)
