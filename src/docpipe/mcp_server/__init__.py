"""Optional hosted Model Context Protocol (MCP) server integration.

The package imports FastMCP lazily, so installing or importing the core Docpipe
SDK does not require the optional MCP server dependency.
"""

from docpipe.mcp_server.server import create_mcp_asgi_app, create_mcp_server

__all__ = ["create_mcp_asgi_app", "create_mcp_server"]
