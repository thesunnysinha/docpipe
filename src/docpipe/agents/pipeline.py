"""Agentic RAG using Microsoft AutoGen."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from docpipe.agents.tools import make_parse_tool, make_search_tool, require_autogen
from docpipe.core.errors import ConfigurationError
from docpipe.core.types import RAGConfig, RAGResult
from docpipe.observability.spans import trace_operation
from docpipe.rag.pipeline import RAGPipeline

_SUPPORTED_LLM_PROVIDERS = {"openai"}


class AgentRAGPipeline:
    """RAG with tool-using AutoGen agents instead of a single LangChain completion."""

    def __init__(
        self,
        config: RAGConfig,
        *,
        enable_reviewer: bool = False,
        enable_parse_tool: bool = False,
        parse_tool_parser: str = "markitdown",
        max_tool_iterations: int = 5,
        max_turns: int = 6,
    ) -> None:
        require_autogen()
        self._config = config
        self._enable_reviewer = enable_reviewer
        self._enable_parse_tool = enable_parse_tool
        self._parse_tool_parser = parse_tool_parser
        self._max_tool_iterations = max_tool_iterations
        self._max_turns = max_turns
        self._rag = RAGPipeline(config)

    def _create_model_client(self) -> Any:
        provider = self._config.llm_provider
        if provider not in _SUPPORTED_LLM_PROVIDERS:
            supported = sorted(_SUPPORTED_LLM_PROVIDERS)
            raise ConfigurationError(
                f"Agent RAG supports llm_provider={supported}; got '{provider}'."
            )
        if provider == "openai":
            from autogen_ext.models.openai import OpenAIChatCompletionClient

            kwargs: dict[str, Any] = {"model": self._config.llm_model}
            if self._config.llm_api_key:
                kwargs["api_key"] = self._config.llm_api_key
            return OpenAIChatCompletionClient(**kwargs)
        raise ConfigurationError(f"Unsupported llm_provider: {provider}")

    def _build_tools(self) -> list[Any]:
        from autogen_core.tools import FunctionTool

        tools: list[Any] = [
            FunctionTool(
                make_search_tool(self._rag),
                description="Search ingested documents for relevant passages.",
                name="search_documents",
            )
        ]
        if self._enable_parse_tool:
            tools.append(
                FunctionTool(
                    make_parse_tool(parser=self._parse_tool_parser),
                    description="Parse a document path or URL into markdown.",
                    name="parse_document",
                )
            )
        return tools

    def _extract_answer(self, task_result: Any) -> str:
        messages = getattr(task_result, "messages", None) or []
        for message in reversed(messages):
            content = getattr(message, "content", None)
            if isinstance(content, str) and content.strip():
                return content.strip()
        return ""

    async def aquery(self, question: str) -> RAGResult:
        """Run agentic RAG asynchronously."""
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.conditions import TextMentionTermination
        from autogen_agentchat.teams import RoundRobinGroupChat

        start = time.perf_counter()
        model_client = self._create_model_client()
        tools = self._build_tools()
        system_message = (
            "You answer questions using the search_documents tool against ingested content. "
            "Cite sources when possible. Reply with TERMINATE when finished."
        )

        researcher = AssistantAgent(
            "researcher",
            model_client=model_client,
            tools=tools,
            system_message=system_message,
            max_tool_iterations=self._max_tool_iterations,
        )

        with trace_operation(
            "docpipe.agents.query",
            gen_ai_operation="chat",
            provider=self._config.llm_provider,
            model=self._config.llm_model,
            docpipe_strategy="autogen",
            docpipe_table_name=self._config.table_name,
        ):
            if self._enable_reviewer:
                reviewer = AssistantAgent(
                    "reviewer",
                    model_client=model_client,
                    system_message=(
                        "Review the researcher's answer for grounding and completeness. "
                        "If acceptable, reply APPROVE and TERMINATE."
                    ),
                )
                team = RoundRobinGroupChat(
                    [researcher, reviewer],
                    termination_condition=TextMentionTermination("TERMINATE"),
                    max_turns=self._max_turns,
                )
                task_result = await team.run(task=question)
            else:
                task_result = await researcher.run(task=question)

        answer = self._extract_answer(task_result)
        chunks = self._rag._retrieve_naive(question)  # noqa: SLF001
        result = self._rag._make_result(question, answer, chunks, None, None)  # noqa: SLF001
        result.metadata["orchestrator"] = "autogen"
        result.metadata["reviewer_enabled"] = self._enable_reviewer
        result.timing_seconds = time.perf_counter() - start
        return result

    def query(self, question: str) -> RAGResult:
        """Run agentic RAG (sync wrapper)."""
        return asyncio.run(self.aquery(question))
