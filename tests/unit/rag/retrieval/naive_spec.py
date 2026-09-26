"""Tests for dense naive retrieval."""

import pytest

from docpipe.plugins.contracts.vectorstore import Equals
from docpipe.rag.retrieval.naive import NaiveStrategy


@pytest.mark.asyncio
async def test_naive_uses_encoder_reader_and_typed_filter(search, reader) -> None:
    result = await NaiveStrategy(search).retrieve("question")

    assert result.chunks[0].source == "report.pdf"
    assert result.chunks[0].page == 3
    assert reader.queries[0].dense_vector == (8.0, 1.0)
    assert reader.queries[0].limit == 5

    await search.dense("question", filter=Equals("tenant", "acme"))
    assert reader.queries[-1].filter == Equals("tenant", "acme")
