"""MCP tool stubs for docpipe agent integrations."""

from __future__ import annotations

from typing import Any


def list_mcp_tools() -> list[dict[str, Any]]:
    """Return docpipe MCP tool descriptors (stub for future MCP server)."""
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
                    "table_name": {"type": "string"},
                },
                "required": ["question", "table_name"],
            },
        },
    ]
