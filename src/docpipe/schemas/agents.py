"""POST /agents/query schemas."""

from __future__ import annotations

from docpipe.schemas.rag import RAGQueryRequest, RAGQueryResponse


class AgentQueryRequest(RAGQueryRequest):
    """Agentic RAG query — extends RAG with agent runtime options."""

    agent_backend: str | None = None
    enable_reviewer: bool = False
    enable_parse_tool: bool = False
    parse_tool_parser: str = "markitdown"
    max_tool_iterations: int = 5
    max_turns: int = 6
    max_steps: int = 5


class AgentQueryResponse(RAGQueryResponse):
    """Same shape as RAG query response."""
