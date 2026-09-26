"""Tests for tenant-safe typed filter composition across strategies."""

from __future__ import annotations

import pytest

from docpipe.plugins.contracts.vectorstore import And, Equals, VectorCapability
from docpipe.rag.retrieval.base import VectorSearch
from docpipe.rag.retrieval.parent_document import ParentDocumentStrategy

from .conftest import EncoderDouble, ReaderDouble


@pytest.mark.asyncio
async def test_parent_expansion_preserves_tenant_filter() -> None:
    reader = ReaderDouble()
    search = VectorSearch(
        reader,
        EncoderDouble(),
        "documents",
        frozenset({VectorCapability.DENSE_SEARCH, VectorCapability.METADATA_FILTER}),
        3,
        default_filter=Equals("tenant", "acme"),
    )

    await ParentDocumentStrategy(search).retrieve("question")

    assert reader.queries[0].filter == Equals("tenant", "acme")
    assert reader.queries[1].filter == And(
        (Equals("tenant", "acme"), Equals("source", "report.pdf"))
    )
