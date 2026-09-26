"""Pgvector conformance against an explicitly configured test database."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.contracts.vectorstore import CollectionRef
from docpipe.testing.vectorstores import assert_vector_store_conformance
from docpipe.vectorstores.pgvector.adapter import PgVectorAdapter
from docpipe.vectorstores.pgvector.configuration import PgVectorConfig
from docpipe.vectorstores.pgvector.queries import PsycopgPgVectorRepository


@pytest.mark.asyncio
async def test_pgvector_contract() -> None:
    dsn = os.getenv("DOCPIPE_TEST_PGVECTOR_DSN")
    if not dsn:
        pytest.skip("DOCPIPE_TEST_PGVECTOR_DSN is not configured")
    config = PgVectorConfig(dsn=dsn)
    repository = PsycopgPgVectorRepository(config)
    collection = CollectionRef(f"test_{uuid4().hex[:12]}")

    async with BoundedBlockingRunner(max_concurrency=2) as runner:
        adapter = PgVectorAdapter(config, repository, runner)
        try:
            await assert_vector_store_conformance(
                adapter.binding,
                collection=collection,
                dimensions=3,
            )
        finally:
            await adapter.delete_collection(collection)
