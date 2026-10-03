"""Agentic RAG on the shared agent runtime (optional extra: ``docpipe-sdk[agents]``).

Compared with the AutoGen and LangGraph backends this one adds, around the same search and parse
tools: input guardrails (prompt-injection and PII checks), a loop guard that stops repeated or
fruitless tool calls, per-tool logging, optional conversation sessions, and tracing.
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from typing import Any

from docpipe.core.errors import ConfigurationError, RAGError
from docpipe.core.schemas.rag import RAGChunk
from docpipe.core.types import RAGConfig, RAGResult
from docpipe.observability.spans import trace_operation
from docpipe.rag.pipeline import RAGPipeline

SYSTEM_PROMPT = (
    "You answer questions using the search_documents tool against ingested content. "
    "Search before answering, cite sources when possible, and say so when the documents do not "
    "contain the answer. Do not repeat a search with the same arguments."
)
MAX_SESSIONS = 500
MAX_QUESTION_CHARS = 8000


def require_runtime() -> None:
    """Raise a configuration error when the optional agents extra is absent."""
    try:
        import langgraph  # noqa: F401
        import structlog  # noqa: F401

        from docpipe.agents._runtime import tool_agent  # noqa: F401
    except ImportError as err:
        raise ConfigurationError(
            "The runtime agent backend requires the agents extra. "
            "Install with: pip install docpipe-sdk[agents]"
        ) from err


class SessionStore:
    """In-memory conversation memory shared by every request, bounded by session count."""

    def __init__(self, max_sessions: int = MAX_SESSIONS) -> None:
        """Create an empty store that forgets the least recently started session when full."""
        from langgraph.checkpoint.memory import InMemorySaver

        self.saver = InMemorySaver()
        self._order: deque[str] = deque()
        self._max_sessions = max_sessions

    def touch(self, session_id: str) -> None:
        """Record use of a session and evict the oldest one beyond the limit."""
        if session_id in self._order:
            return
        self._order.append(session_id)
        while len(self._order) > self._max_sessions:
            self.saver.delete_thread(self._order.popleft())


_sessions: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Return the process-wide session store, creating it on first use."""
    global _sessions
    if _sessions is None:
        _sessions = SessionStore()
    return _sessions


def _ensure_stdlib_logging() -> None:
    """Send the runtime's structured logs through standard logging unless already configured."""
    import structlog

    if not structlog.is_configured():
        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.KeyValueRenderer(key_order=["event"]),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
        )


def _format_chunks(chunks: tuple[RAGChunk, ...]) -> str:
    lines: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        page = f", page {chunk.page}" if chunk.page is not None else ""
        lines.append(f"[{index}] ({chunk.source or 'unknown'}{page})\n{chunk.content}")
    return "\n\n".join(lines)


class RuntimeRAGPipeline:
    """RAG with a tool-using agent that has guardrails, a loop guard and optional sessions."""

    def __init__(
        self,
        config: RAGConfig,
        *,
        enable_parse_tool: bool = False,
        parse_tool_parser: str = "markitdown",
        max_steps: int = 5,
        rag: RAGPipeline | None = None,
        sessions: SessionStore | None = None,
    ) -> None:
        """Prepare the agent for one request; heavy imports happen here, not at module import."""
        require_runtime()
        _ensure_stdlib_logging()
        self._config = config
        self._enable_parse_tool = enable_parse_tool
        self._parse_tool_parser = parse_tool_parser
        self._max_steps = max_steps
        self._rag = rag or RAGPipeline(config)
        self._sessions = sessions or get_session_store()

    def _build_tools(self, retrieved: list[RAGChunk]) -> list[Any]:
        """Wrap docpipe search (and optionally parse) as LangChain tools."""
        from langchain_core.tools import tool

        from docpipe.agents.tools import make_parse_tool

        rag = self._rag

        @tool
        def search_documents(query: str) -> str:
            """Search ingested documents for passages relevant to a question or topic."""
            chunks = rag.retrieve_chunks(query)
            retrieved.extend(chunks)
            return _format_chunks(chunks) if chunks else "No relevant documents found."

        tools: list[Any] = [search_documents]
        if self._enable_parse_tool:
            parse = make_parse_tool(parser=self._parse_tool_parser)
            tools.append(tool("parse_document")(parse))
        return tools

    def _build_agent(self, retrieved: list[RAGChunk], checkpointer: Any) -> Any:
        from docpipe.agents._runtime.tool_agent import ToolAgent

        agent = ToolAgent(
            name="docpipe-agent",
            system_prompt=SYSTEM_PROMPT,
            tools=self._build_tools(retrieved),
            llm=self._rag._llm,  # noqa: SLF001 - the pipeline owns the configured chat model
            provider_name=f"{self._config.llm_provider}:{self._config.llm_model}",
            checkpointer=checkpointer,
        )
        agent.RECURSION_LIMIT = max(4, self._max_steps * 2 + 2)
        return agent

    @staticmethod
    def _guard_question(question: str) -> str:
        from docpipe.agents._runtime.guardrails import PIIGuardrail, SecurityGuardrail

        class QuestionGuardrail(SecurityGuardrail):
            """docpipe accepts one-character questions; the default minimum is two."""

            MIN_CHARS = 1
            MAX_CHARS = MAX_QUESTION_CHARS

        return PIIGuardrail().evaluate(QuestionGuardrail().evaluate(question))

    async def aquery(self, question: str, session_id: str | None = None) -> RAGResult:
        """Answer a question; pass ``session_id`` to continue an earlier conversation."""
        from langgraph.checkpoint.memory import InMemorySaver

        from docpipe.agents._runtime.errors import AgentServiceError

        start = time.perf_counter()
        try:
            guarded = self._guard_question(question)
        except AgentServiceError as err:
            raise RAGError(err.message) from err
        store = self._sessions if session_id else None
        checkpointer = store.saver if store is not None else InMemorySaver()
        if store is not None and session_id:
            store.touch(session_id)
        retrieved: list[RAGChunk] = []
        agent = self._build_agent(retrieved, checkpointer)
        await agent.startup()
        with trace_operation(
            "docpipe.agents.runtime",
            gen_ai_operation="chat",
            provider=self._config.llm_provider,
            model=self._config.llm_model,
            docpipe_strategy="runtime",
            docpipe_table_name=self._config.table_name,
        ):
            try:
                outcome = await agent.execute(
                    guarded, session_id or uuid.uuid4().hex, uuid.uuid4().hex
                )
            except AgentServiceError as err:
                raise RAGError(err.message) from err
        unique = tuple({(c.source, c.page, c.content): c for c in retrieved}.values())
        result = self._rag.result_from_chunks(question, outcome.response, unique)
        result.strategy = "runtime"
        result.timing_seconds = time.perf_counter() - start
        result.metadata["agent"] = "runtime"
        result.metadata["tools_executed"] = outcome.tools_executed
        result.metadata["session_id"] = session_id
        return result
