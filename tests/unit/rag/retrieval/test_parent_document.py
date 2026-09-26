"""Tests for source-window expansion through typed metadata filters."""

import pytest

from docpipe.plugins.contracts.vectorstore import Equals, VectorMatch
from docpipe.rag.retrieval.parent_document import ParentDocumentStrategy


@pytest.mark.asyncio
async def test_parent_document_expands_each_unique_source(search, reader) -> None:
    reader.matches = (VectorMatch("seed", 0.9, "seed", {"source": "a.pdf"}, "a.pdf"),)
    strategy = ParentDocumentStrategy(search, window_size=2)

    result = await strategy.retrieve("question")

    assert len(reader.queries) == 2
    assert reader.queries[1].filter == Equals("source", "a.pdf")
    assert len(result.chunks) == 1
