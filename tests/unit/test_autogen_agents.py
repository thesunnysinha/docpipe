"""Tests for AutoGen agent orchestration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docpipe.agents.pipeline import AgentRAGPipeline
from docpipe.agents.tools import require_autogen
from docpipe.core.errors import ConfigurationError
from docpipe.core.types import RAGConfig


def _rag_config() -> RAGConfig:
    return RAGConfig(
        connection_string="postgresql://test/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
    )


def test_require_autogen_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("autogen"):
            raise ImportError("no autogen")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ConfigurationError, match="AutoGen is not installed"):
        require_autogen()


def test_agent_rag_pipeline_rejects_unsupported_provider() -> None:
    config = _rag_config().model_copy(update={"llm_provider": "ollama"})
    with (
        patch("docpipe.agents.tools.require_autogen"),
        patch("docpipe.agents.pipeline.RAGPipeline", return_value=MagicMock()),
    ):
        pipeline = AgentRAGPipeline(config)
    with pytest.raises(ConfigurationError, match="supports llm_provider"):
        pipeline._create_model_client()


@pytest.mark.asyncio
async def test_agent_rag_pipeline_runs_researcher_agent() -> None:
    config = _rag_config()
    mock_task_result = MagicMock()
    mock_task_result.messages = [MagicMock(content="Final grounded answer")]

    with (
        patch("docpipe.agents.tools.require_autogen"),
        patch("docpipe.agents.pipeline.RAGPipeline") as mock_rag_cls,
        patch("autogen_agentchat.agents.AssistantAgent") as mock_agent_cls,
    ):
        mock_rag = mock_rag_cls.return_value
        mock_rag._retrieve_naive.return_value = []
        mock_rag._make_result.return_value = MagicMock(
            answer="",
            metadata={},
            timing_seconds=0.0,
        )

        mock_agent = mock_agent_cls.return_value
        mock_agent.run = AsyncMock(return_value=mock_task_result)

        pipeline = AgentRAGPipeline(config)
        pipeline._create_model_client = MagicMock(return_value=MagicMock())
        result = await pipeline.aquery("What is the total?")

    mock_agent.run.assert_awaited_once()
    mock_rag._make_result.assert_called_once()
    assert result.metadata["orchestrator"] == "autogen"
