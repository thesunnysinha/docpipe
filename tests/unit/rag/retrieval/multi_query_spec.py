"""Tests for deterministic multi-query retrieval merging."""

import pytest

from docpipe.rag.retrieval.multi_query import MultiQueryStrategy

from .conftest import RewriterDouble


@pytest.mark.asyncio
async def test_multi_query_deduplicates_records_and_reports_variants(search, reader) -> None:
    rewriter = RewriterDouble("variant one\nvariant two\nvariant three")
    strategy = MultiQueryStrategy(
        search,
        rewriter,
        "Generate {n} variants for {question}",
        count=2,
    )

    result = await strategy.retrieve("original")

    assert len(reader.queries) == 3
    assert len(result.chunks) == 1
    assert result.metadata["query_variants"] == ("variant one", "variant two")
