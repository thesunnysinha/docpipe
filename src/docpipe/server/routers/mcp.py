"""MCP tool discovery and invocation."""

from __future__ import annotations

from fastapi import APIRouter

from docpipe.observability.spans import trace_operation
from docpipe.schemas.mcp import McpCallRequest, McpCallResponse, McpToolsResponse
from docpipe.server.deps import Auth, McpServiceDep
from docpipe.server.router_errors import handle_docpipe_errors

router = APIRouter(tags=["mcp"])


@router.get("/mcp/tools", response_model=McpToolsResponse)
async def mcp_tools(_: Auth, service: McpServiceDep) -> McpToolsResponse:
    return service.list_tools()


@router.post("/mcp/call", response_model=McpCallResponse)
@handle_docpipe_errors
async def mcp_call(
    req: McpCallRequest,
    _: Auth,
    service: McpServiceDep,
) -> McpCallResponse:
    with trace_operation("docpipe.mcp.call", docpipe_tool=req.tool):
        return await service.call(req)
