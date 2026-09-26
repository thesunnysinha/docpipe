"""Bounded LangChain model adapter for RAG answers and streaming."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.core.errors import ConfigurationError
from docpipe.core.types import RAGConfig, TokenUsage
from docpipe.observability.tokens import (
    UsageCallbackHandler,
    extract_usage_from_langchain_response,
    merge_usage,
)
from docpipe.rag.generation import GeneratedAnswer, normalize_content

_END = object()


class LangChainAnswerGenerator:
    """Keep synchronous provider models and messaging behind a bounded port."""

    def __init__(self, config: RAGConfig, llm: Any, runner: BoundedBlockingRunner) -> None:
        self._config = config
        self._llm = llm
        self._runner = runner
        self._usage_handler = UsageCallbackHandler()
        self.last_usage: TokenUsage | None = None

    async def generate(self, question: str, context: str) -> GeneratedAnswer:
        """Generate text or structured output with provider-independent usage."""
        messages = self._messages(question, context)
        self._usage_handler.reset()
        options = {"callbacks": [self._usage_handler]}
        schema = self._config.output_model or self._config.response_format
        if schema is not None:
            structured_llm = self._llm.with_structured_output(schema)
            result = await self._runner.run(structured_llm.invoke, messages, options)
            text = result.model_dump_json() if hasattr(result, "model_dump_json") else str(result)
            usage = self._usage_handler.usage
            self.last_usage = usage
            return GeneratedAnswer(text, structured=result, usage=usage)
        response = await self._runner.run(self._llm.invoke, messages, options)
        usage = merge_usage(
            self._usage_handler.usage,
            extract_usage_from_langchain_response(response),
        )
        self.last_usage = usage
        return GeneratedAnswer(normalize_content(response.content), usage=usage)

    async def stream(self, question: str, context: str) -> AsyncIterator[str]:
        """Yield model fragments without materializing an entire stream."""
        messages = self._messages(question, context)
        self._usage_handler.reset()
        self.last_usage = None
        iterator = await self._runner.run(
            self._llm.stream, messages, {"callbacks": [self._usage_handler]}
        )
        last_chunk: Any = None
        while True:
            chunk = await self._runner.run(_next_chunk, iterator)
            if chunk is _END:
                break
            last_chunk = chunk
            text = normalize_content(chunk.content)
            if text:
                yield text
        if last_chunk is not None:
            self.last_usage = merge_usage(
                self._usage_handler.usage,
                extract_usage_from_langchain_response(last_chunk),
            )

    def _messages(self, question: str, context: str) -> list[Any]:
        """Render a configured prompt and preserve typed conversation turns."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        prompt = self._config.system_prompt
        if not prompt or not prompt.strip():
            raise ConfigurationError("system_prompt is required for RAG generation")
        system_text = prompt.format(context=context, question=question)
        messages: list[Any] = [SystemMessage(content=system_text)]
        for turn in self._config.history:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                messages.append(AIMessage(content=turn["content"]))
        messages.append(HumanMessage(content=question))
        return messages


def _next_chunk(iterator: Iterator[Any]) -> Any:
    try:
        return next(iterator)
    except StopIteration:
        return _END
