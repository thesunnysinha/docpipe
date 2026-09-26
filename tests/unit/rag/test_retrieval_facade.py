"""Retrieval-only SDK behavior used by agent tools and evaluators."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docpipe.core.types import RAGChunk, RAGConfig
from docpipe.rag.pipeline import RAGPipeline


@pytest.mark.asyncio
async def test_agent_retrieval_does_not_invoke_answer_generator() -> None:
    config = RAGConfig(
        connection_string="postgresql://test/db",
        table_name="documents",
        embedding_provider="openai",
        embedding_model="model",
        llm_provider="openai",
        llm_model="model",
    )
    with (
        patch.object(RAGPipeline, "_create_embeddings", return_value=MagicMock()),
        patch.object(RAGPipeline, "_create_llm", return_value=MagicMock()),
        patch("docpipe.rag.pipeline.build_rag_coordinator", new_callable=AsyncMock) as build,
    ):
        prepared = MagicMock(chunks=(RAGChunk(content="text", score=0.9, source="a"),))
        build.return_value = (MagicMock(prepare=AsyncMock(return_value=prepared)), MagicMock())
        chunks = await RAGPipeline(config).aretrieve_chunks("question")
    assert chunks[0].source == "a"
    build.return_value[0].prepare.assert_awaited_once_with("question")
