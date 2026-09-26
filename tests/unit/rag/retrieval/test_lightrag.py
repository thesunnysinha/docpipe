"""Tests for optional graph retrieval and deterministic dense fallback."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from docpipe.core.errors import ConfigurationError
from docpipe.rag.retrieval.lightrag import LightRAGStrategy


@pytest.mark.asyncio
async def test_graph_result_is_cited_without_logging_working_directory(search) -> None:
    client = AsyncMock(return_value="graph result")
    result = await LightRAGStrategy(
        search, working_dir="/sensitive/workdir", query_graph=client
    ).retrieve("question")

    assert result.chunks[0].source == "lightrag"
    assert result.chunks[0].content == "graph result"
    assert result.metadata == {"lightrag_working_dir": "/sensitive/workdir"}
    client.assert_awaited_once_with("question", "/sensitive/workdir")


@pytest.mark.asyncio
async def test_empty_graph_answer_uses_dense_reader(search, reader) -> None:
    result = await LightRAGStrategy(
        search, working_dir="index", query_graph=AsyncMock(return_value="")
    ).retrieve("question")

    assert result.chunks[0].source == "report.pdf"
    assert len(reader.queries) == 1


@pytest.mark.asyncio
async def test_working_directory_required_before_client_call(search) -> None:
    client = AsyncMock()
    with pytest.raises(ConfigurationError, match="lightrag_working_dir"):
        await LightRAGStrategy(search, working_dir=None, query_graph=client).retrieve("q")
    client.assert_not_awaited()
