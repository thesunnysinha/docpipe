"""MCP tool discovery and invocation."""

from __future__ import annotations

from docpipe.agents.mcp_tools import execute_mcp_tool, list_mcp_tools
from docpipe.schemas.mcp import McpCallRequest, McpCallResponse, McpToolDescriptor, McpToolsResponse
from docpipe.server.services.documents import DocumentService
from docpipe.server.services.rag import RAGService


class McpService:
    """Expose document and RAG services through the supported MCP tool set."""

    def __init__(self, document_service: DocumentService, rag_service: RAGService) -> None:
        """Reuse application-injected document and RAG service instances."""
        self._documents = document_service
        self._rag = rag_service

    def list_tools(self) -> McpToolsResponse:
        """Return descriptors for the tools supported by this server."""
        tools = [McpToolDescriptor(**item) for item in list_mcp_tools()]
        return McpToolsResponse(tools=tools)

    async def call(self, req: McpCallRequest) -> McpCallResponse:
        """Dispatch a validated tool request to parsing or RAG services.

        Calls may access source documents, vector stores, and model providers;
        tool and service errors propagate to the transport/router error handler.
        """
        result = await execute_mcp_tool(
            req.tool,
            req.arguments,
            document_service=self._documents,
            rag_service=self._rag,
        )
        return McpCallResponse(tool=req.tool, result=result)
