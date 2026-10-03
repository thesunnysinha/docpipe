"""POST /agents/query schemas."""

from __future__ import annotations

from pydantic import Field

from docpipe.schemas.rag import RAGQueryRequest, RAGQueryResponse


class AgentQueryRequest(RAGQueryRequest):
    """Agentic RAG query — extends RAG with agent runtime options."""

    agent_backend: str | None = Field(
        default=None,
        description=(
            "Agent framework: autogen (default), langgraph, or runtime (guardrails, loop guard, "
            "sessions; needs the docpipe-sdk[agents] extra)."
        ),
    )
    session_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description=(
            "Continue an earlier conversation. Runtime backend only; sessions are kept in "
            "memory by this process and are lost on restart."
        ),
    )
    enable_reviewer: bool = Field(
        default=False,
        description="Run a reviewer agent pass on the draft answer.",
    )
    enable_parse_tool: bool = Field(
        default=False,
        description="Expose document parsing as an agent tool.",
    )
    parse_tool_parser: str = Field(
        default="markitdown",
        description="Parser used by the parse tool.",
    )
    max_tool_iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum tool-call iterations per agent.",
    )
    max_turns: int = Field(default=6, ge=1, le=30, description="Maximum agent conversation turns.")
    max_steps: int = Field(default=5, ge=1, le=30, description="Maximum planner steps.")


class AgentQueryResponse(RAGQueryResponse):
    """Agentic RAG result — same shape as a standard RAG response."""
