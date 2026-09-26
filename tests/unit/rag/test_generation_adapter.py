"""Tests for isolated model messaging, usage, and token streaming."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from docpipe.core.errors import ConfigurationError
from docpipe.core.types import RAGConfig
from docpipe.rag.generation import LangChainAnswerGenerator


def _config(**overrides: object) -> RAGConfig:
    values: dict[str, object] = {
        "connection_string": "postgresql://test/db",
        "table_name": "documents",
        "embedding_provider": "openai",
        "embedding_model": "model",
        "llm_provider": "openai",
        "llm_model": "model",
        "system_prompt": "Use {context} for {question}",
        "history": [
            {"role": "user", "content": "older question"},
            {"role": "assistant", "content": "older answer"},
        ],
    }
    values.update(overrides)
    return RAGConfig.model_validate(values)


@pytest.mark.asyncio
async def test_generation_preserves_history_content_usage_and_seams(active_runner) -> None:
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(
        content="grounded answer",
        usage_metadata={"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
    )
    generator = LangChainAnswerGenerator(_config(), llm, active_runner)

    result = await generator.generate("new question", "context text")

    messages = llm.invoke.call_args.args[0]
    assert [type(message).__name__ for message in messages] == [
        "SystemMessage",
        "HumanMessage",
        "AIMessage",
        "HumanMessage",
    ]
    assert messages[0].content == "Use context text for new question"
    assert result.answer == "grounded answer"
    assert result.usage is not None and result.usage.total_tokens == 6


@pytest.mark.asyncio
async def test_missing_prompt_fails_before_model_call(active_runner) -> None:
    llm = MagicMock()
    generator = LangChainAnswerGenerator(_config(system_prompt=None), llm, active_runner)
    with pytest.raises(ConfigurationError, match="system_prompt"):
        await generator.generate("question", "context")
    llm.invoke.assert_not_called()


@pytest.mark.asyncio
async def test_structured_answer_retains_original_value(active_runner) -> None:
    llm = MagicMock()
    structured = MagicMock()
    structured.model_dump_json.return_value = '{"total":42}'
    llm.with_structured_output.return_value.invoke.return_value = structured
    output_model = type("Invoice", (), {})
    generator = LangChainAnswerGenerator(_config(output_model=output_model), llm, active_runner)

    answer = await generator.generate("question", "context")

    llm.with_structured_output.assert_called_once_with(output_model)
    assert answer.structured is structured
    assert answer.answer == '{"total":42}'


@pytest.mark.asyncio
async def test_stream_normalizes_provider_blocks_and_records_usage(active_runner) -> None:
    llm = MagicMock()
    llm.stream.return_value = iter(
        [
            MagicMock(content="Hello"),
            MagicMock(
                content=[{"text": " world"}],
                usage_metadata={"input_tokens": 2, "output_tokens": 2, "total_tokens": 4},
            ),
        ]
    )
    generator = LangChainAnswerGenerator(_config(), llm, active_runner)

    tokens = [token async for token in generator.stream("question", "context")]

    assert tokens == ["Hello", " world"]
    assert generator.last_usage is not None and generator.last_usage.total_tokens == 4
