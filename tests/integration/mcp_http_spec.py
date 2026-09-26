"""End-to-end checks for the optional mounted MCP HTTP transport."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

pytest.importorskip("fastmcp")

from docpipe.config.settings import DocpipeSettings
from docpipe.server.app import create_app


def test_mcp_mount_requires_bearer_token_and_serves_streamable_http() -> None:
    """The mounted MCP protocol is independently protected from REST Basic Auth."""
    token = "mcp-integration-token-" + ("x" * 40)
    app = create_app(
        DocpipeSettings(
            auth_enabled=False,
            health_check_db=False,
            mcp_server_enabled=True,
            mcp_operator_tokens=(SecretStr(token),),
            mcp_allowed_hosts=("testserver",),
        )
    )
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "docpipe-test", "version": "1.0"},
        },
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    with TestClient(app) as client:
        health = client.get("/mcp/health")
        denied = client.post("/mcp", json=initialize, headers=headers)
        allowed = client.post(
            "/mcp",
            json=initialize,
            headers={**headers, "Authorization": f"Bearer {token}"},
        )

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert denied.status_code == 401
    assert allowed.status_code == 200
