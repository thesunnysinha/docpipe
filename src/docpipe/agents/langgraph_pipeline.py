"""LangGraph-based agentic RAG (optional extra)."""

from __future__ import annotations

import time

from docpipe.core.errors import ConfigurationError
from docpipe.core.types import RAGConfig, RAGResult
from docpipe.observability.spans import trace_operation
from docpipe.rag.pipeline import RAGPipeline


def require_langgraph() -> None:
    try:
        import langgraph  # noqa: F401
    except ImportError as err:
        raise ConfigurationError(
            "LangGraph agents require the langgraph extra. "
            "Install with: pip install docpipe-sdk[langgraph]"
        ) from err


class LangGraphRAGPipeline:
    """Minimal LangGraph agent that delegates retrieval to RAGPipeline tools."""

    def __init__(self, config: RAGConfig, *, max_steps: int = 5) -> None:
        require_langgraph()
        self._config = config
        self._max_steps = max_steps
        self._rag = RAGPipeline(config)

    def query(self, question: str) -> RAGResult:
        from langchain_core.messages import HumanMessage
        from langgraph.prebuilt import create_react_agent

        start = time.perf_counter()

        from langchain_core.tools import tool

        @tool
        def search_documents(query: str) -> str:
            """Search ingested documents for relevant passages."""
            chunks = self._rag._retrieve_naive(query)  # noqa: SLF001
            return self._rag._build_context(chunks)  # noqa: SLF001

        llm = self._rag._llm
        agent = create_react_agent(llm, tools=[search_documents])
        with trace_operation("docpipe.agents.langgraph"):
            state = agent.invoke(
                {"messages": [HumanMessage(content=question)]},
                config={"recursion_limit": self._max_steps},
            )
        messages = state.get("messages", [])
        answer = ""
        for msg in reversed(messages):
            content = getattr(msg, "content", None)
            if isinstance(content, str) and content.strip():
                answer = content
                break

        chunks = self._rag._retrieve_naive(question)  # noqa: SLF001
        result = self._rag._make_result(question, answer, chunks, None, None)  # noqa: SLF001
        result.strategy = "langgraph"
        result.timing_seconds = time.perf_counter() - start
        result.metadata["agent"] = "langgraph"
        return result
