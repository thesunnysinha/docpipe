"""MCP tool discovery and invocation schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from docpipe.schemas.base import ApiRequest, ApiResponse


class McpToolDescriptor(ApiResponse):
    """MCP-compatible tool metadata."""

    name: str = Field(..., min_length=1, description="Tool identifier.")
    description: str = Field(..., min_length=1, description="Human-readable summary.")
    input_schema: dict[str, Any] = Field(..., description="JSON Schema for tool arguments.")


class McpToolsResponse(ApiResponse):
    """List of tools exposed by the docpipe MCP surface."""

    tools: list[McpToolDescriptor] = Field(default_factory=list)


class McpCallRequest(ApiRequest):
    """Invoke a docpipe MCP tool."""

    tool: str = Field(..., min_length=1, description="Tool name from GET /mcp/tools.")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific arguments.",
    )


class McpCallResponse(ApiResponse):
    """Result of an MCP tool invocation."""

    tool: str = Field(..., description="Tool that was executed.")
    result: dict[str, Any] = Field(default_factory=dict, description="Structured tool output.")
