"""MCP tool descriptors and execution for docpipe agent integrations."""

from __future__ import annotations

from typing import Any

from docpipe.core.errors import ConfigurationError


def list_mcp_tools() -> list[dict[str, Any]]:
    """Return docpipe MCP tool descriptors."""
    return [
        {
            "name": "docpipe_parse",
            "description": "Parse a document to markdown using docpipe parsers.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "parser": {"type": "string", "default": "auto"},
                    "tier": {"type": "string", "enum": ["fast", "balanced", "quality"]},
                    "preset": {
                        "type": "string",
                        "enum": ["fast", "balanced", "quality", "agents"],
                    },
                },
                "required": ["source"],
            },
        },
        {
            "name": "docpipe_rag_query",
            "description": "Query ingested documents with RAG.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "connection_string": {"type": "string"},
                    "table_name": {"type": "string"},
                    "embedding_provider": {"type": "string"},
                    "embedding_model": {"type": "string"},
                    "llm_provider": {"type": "string"},
                    "llm_model": {"type": "string"},
                    "preset": {
                        "type": "string",
                        "enum": ["fast", "balanced", "quality", "agents"],
                    },
                },
                "required": [
                    "question",
                    "connection_string",
                    "table_name",
                    "embedding_provider",
                    "embedding_model",
                    "llm_provider",
                    "llm_model",
                ],
            },
        },
    ]


async def execute_mcp_tool(
    tool: str,
    arguments: dict[str, Any],
    *,
    document_service: Any,
    rag_service: Any,
) -> dict[str, Any]:
    """Run a named MCP tool using server services."""
    if tool == "docpipe_parse":
        from docpipe.schemas import ParseRequest

        source = arguments.get("source")
        if not source:
            raise ConfigurationError("docpipe_parse requires 'source'")
        req = ParseRequest(
            source=str(source),
            parser=arguments.get("parser"),
            tier=arguments.get("tier"),
            preset=arguments.get("preset"),
        )
        resp = await document_service.parse(req)
        return {
            "source": resp.source,
            "format": resp.format,
            "content": resp.content,
            "metadata": resp.metadata,
        }

    if tool == "docpipe_rag_query":
        from docpipe.schemas import RAGQueryRequest

        question = arguments.get("question")
        if not question:
            raise ConfigurationError("docpipe_rag_query requires 'question'")
        req = RAGQueryRequest(
            question=str(question),
            connection_string=str(arguments["connection_string"]),
            table_name=str(arguments["table_name"]),
            embedding_provider=str(arguments["embedding_provider"]),
            embedding_model=str(arguments["embedding_model"]),
            llm_provider=str(arguments["llm_provider"]),
            llm_model=str(arguments["llm_model"]),
            preset=arguments.get("preset"),
            system_prompt=str(
                arguments.get(
                    "system_prompt",
                    "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:",
                )
            ),
            hyde_prompt=str(arguments.get("hyde_prompt", "Hypothetical passage for: {question}")),
            multi_query_prompt=str(
                arguments.get(
                    "multi_query_prompt",
                    "Generate {n} variants of: {question}",
                )
            ),
            auto_strategy_prompt=str(
                arguments.get("auto_strategy_prompt", "Reply naive for: {question}")
            ),
        )
        resp = await rag_service.query(req)
        return {
            "answer": resp.answer,
            "chunks": [c.model_dump() for c in resp.chunks],
            "usage": resp.usage.model_dump(exclude_none=True) if resp.usage else None,
        }

    raise ConfigurationError(f"Unknown MCP tool: {tool}")
