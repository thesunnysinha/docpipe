"""MCP tool discovery and invocation."""

from __future__ import annotations

from docpipe.agents.mcp_tools import execute_mcp_tool, list_mcp_tools
from docpipe.registry.registry import PluginRegistry
from docpipe.schemas.mcp import McpCallRequest, McpCallResponse, McpToolDescriptor, McpToolsResponse
from docpipe.server.services.documents import DocumentService
from docpipe.server.services.rag import RAGService


class McpService:
    def __init__(self, registry: PluginRegistry, rag_service: RAGService) -> None:
        self._documents = DocumentService(registry)
        self._rag = rag_service

    def list_tools(self) -> McpToolsResponse:
        tools = [McpToolDescriptor(**item) for item in list_mcp_tools()]
        return McpToolsResponse(tools=tools)

    async def call(self, req: McpCallRequest) -> McpCallResponse:
        result = await execute_mcp_tool(
            req.tool,
            req.arguments,
            document_service=self._documents,
            rag_service=self._rag,
        )
        return McpCallResponse(tool=req.tool, result=result)
