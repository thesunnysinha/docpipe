"""Tests for routing the runtime agent backend through AgentService."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("langgraph.runtime")
pytest.importorskip("structlog")

from docpipe.core.schemas.rag import RAGResult  # noqa: E402


def _request(**overrides: Any) -> Any:
    from docpipe.schemas import AgentQueryRequest

    fields: dict[str, Any] = {
        "question": "q",
        "connection_string": "postgresql://test/db",
        "table_name": "docs",
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-small",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "system_prompt": "Answer from {context}. Question: {question}",
    }
    return AgentQueryRequest(**{**fields, **overrides})


def _result(answer: str) -> RAGResult:
    return RAGResult(
        query="q", answer=answer, strategy="x", chunks=[], sources=[], timing_seconds=0.1
    )


@pytest.mark.asyncio
async def test_service_routes_the_runtime_backend() -> None:
    from docpipe.config.settings import DocpipeSettings
    from docpipe.server.services.agents import AgentService

    stub = MagicMock()
    stub.aquery = AsyncMock(return_value=_result("from runtime"))
    with patch("docpipe.agents.runtime_pipeline.RuntimeRAGPipeline", return_value=stub):
        response = await AgentService(DocpipeSettings()).query(
            _request(agent_backend="runtime", session_id="abc")
        )

    assert response.answer == "from runtime"
    stub.aquery.assert_called_once_with("q", "abc")


@pytest.mark.asyncio
async def test_service_still_defaults_to_autogen_without_touching_the_runtime() -> None:
    from docpipe.config.settings import DocpipeSettings
    from docpipe.server.services.agents import AgentService

    autogen = MagicMock()
    autogen.query = MagicMock(return_value=_result("from autogen"))
    with (
        patch("docpipe.agents.pipeline.AgentRAGPipeline", return_value=autogen),
        patch("docpipe.agents.runtime_pipeline.RuntimeRAGPipeline") as runtime,
    ):
        response = await AgentService(DocpipeSettings()).query(_request())

    assert response.answer == "from autogen"
    runtime.assert_not_called()
