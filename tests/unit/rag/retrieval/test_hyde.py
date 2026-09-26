"""Tests for hypothetical-document retrieval."""

import pytest

from docpipe.rag.retrieval.hyde import HydeStrategy

from .conftest import RewriterDouble


@pytest.mark.asyncio
async def test_hyde_searches_generated_passage_and_returns_metadata(search, reader) -> None:
    rewriter = RewriterDouble("hypothetical revenue passage")
    strategy = HydeStrategy(search, rewriter, "Write a passage for {question}")

    result = await strategy.retrieve("What was revenue?")

    assert reader.queries[0].dense_vector == (
        float(len("hypothetical revenue passage")),
        1.0,
    )
    assert result.metadata["hypothetical_doc"] == "hypothetical revenue passage"
