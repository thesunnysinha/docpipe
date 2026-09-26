"""Authenticated HTTP routes for discovering and invoking Docpipe MCP tools.

These endpoints expose the server's configured tool catalog and dispatch
requests through the application-scoped MCP service. Access is governed by the
server's normal ``Auth`` dependency; this router does not implement separate
per-tool or per-tenant authorization.
"""

from __future__ import annotations

from fastapi import APIRouter

from docpipe.observability.spans import trace_operation
from docpipe.schemas.mcp import McpCallRequest, McpCallResponse, McpToolsResponse
from docpipe.server.deps import Auth, McpServiceDep
from docpipe.server.router_errors import handle_docpipe_errors

router = APIRouter(tags=["mcp"])


@router.get("/mcp/tools", response_model=McpToolsResponse)
async def mcp_tools(_: Auth, service: McpServiceDep) -> McpToolsResponse:
    """List the MCP tools exposed by the configured server runtime.

    Args:
        _: Auth dependency that enforces server-level authentication when
            enabled.
        service: Application-scoped service that constructs the tool catalog.

    Returns:
        Tool names and their public input schemas.

    Raises:
        HTTPException: Authentication failures are raised by the dependency;
            service failures are handled by the server's global handlers.
    """
    return service.list_tools()


@router.post("/mcp/call", response_model=McpCallResponse)
@handle_docpipe_errors
async def mcp_call(
    req: McpCallRequest,
    _: Auth,
    service: McpServiceDep,
) -> McpCallResponse:
    """Invoke one configured MCP tool with a validated request payload.

    Args:
        req: Tool name and JSON arguments validated by the request schema.
        _: Auth dependency that enforces server-level authentication when
            enabled.
        service: Application-scoped dispatcher for configured MCP tools.

    Returns:
        Tool result wrapped in the public MCP call response schema.

    Raises:
        HTTPException: Authentication failures are raised by the dependency;
            recognized Docpipe integration errors are mapped by the shared
            route error wrapper. Unexpected failures use global error handling.

    Side effects:
        The selected tool may read configured sources, call remote providers,
        or mutate the vector store depending on its implementation.
    """
    with trace_operation("docpipe.mcp.call", docpipe_tool=req.tool):
        return await service.call(req)
