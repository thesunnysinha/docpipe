"""Unit tests for MCP tool discovery and invocation."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from docpipe.server.app import create_app


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_mcp_tools_lists_docpipe_tools(client):
    resp = client.get("/mcp/tools")

    assert resp.status_code == 200
    names = {tool["name"] for tool in resp.json()["tools"]}
    assert names == {"docpipe_parse", "docpipe_rag_query"}


@patch("docpipe.server.services.mcp.execute_mcp_tool", new_callable=AsyncMock)
def test_mcp_call_parse(mock_execute, client):
    mock_execute.return_value = {
        "source": "/tmp/a.pdf",
        "format": "text",
        "content": "hello",
        "metadata": {},
    }

    resp = client.post(
        "/mcp/call",
        json={"tool": "docpipe_parse", "arguments": {"source": "/tmp/a.pdf"}},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["tool"] == "docpipe_parse"
    assert body["result"]["content"] == "hello"
    mock_execute.assert_awaited_once()
