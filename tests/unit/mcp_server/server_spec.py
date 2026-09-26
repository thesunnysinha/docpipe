"""Hosted Streamable HTTP MCP server assembly tests."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from docpipe.config.settings import DocpipeSettings
from docpipe.core.errors import ConfigurationError
from docpipe.mcp_server.server import create_mcp_asgi_app, create_mcp_server


class FakeTokenVerifier:
    def __init__(self) -> None:
        self.required_scopes: list[str] = []


class FakeFastMCP:
    def __init__(self, name: str, **kwargs: Any) -> None:
        self.name = name
        self.options = kwargs
        self.tools: dict[str, tuple[Any, dict[str, Any]]] = {}
        self.routes: dict[str, Any] = {}
        self.http_options: dict[str, Any] | None = None

    def tool(self, **options: Any) -> Any:
        def register(function: Any) -> Any:
            self.tools[options["name"]] = (function, options)
            return function

        return register

    def custom_route(self, path: str, *, methods: list[str]) -> Any:
        def register(function: Any) -> Any:
            self.routes[path] = (function, methods)
            return function

        return register

    def http_app(self, **options: Any) -> object:
        self.http_options = options
        return self


def _install_fake_fastmcp(monkeypatch: pytest.MonkeyPatch) -> None:
    fastmcp = types.ModuleType("fastmcp")
    fastmcp.__path__ = []  # type: ignore[attr-defined]
    fastmcp.FastMCP = FakeFastMCP  # type: ignore[attr-defined]
    server_package = types.ModuleType("fastmcp.server")
    server_package.__path__ = []  # type: ignore[attr-defined]
    auth = types.ModuleType("fastmcp.server.auth")
    auth.TokenVerifier = FakeTokenVerifier  # type: ignore[attr-defined]
    auth.AccessToken = type("AccessToken", (), {})  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fastmcp", fastmcp)
    monkeypatch.setitem(sys.modules, "fastmcp.server", server_package)
    monkeypatch.setitem(sys.modules, "fastmcp.server.auth", auth)


def test_server_registers_precise_read_only_tools_and_separate_health_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_fastmcp(monkeypatch)
    settings = DocpipeSettings()

    server = create_mcp_server(
        object(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        settings,
        operator_tokens=["x" * 40],
    )

    assert set(server.tools) == {"docpipe_parse", "docpipe_rag_query"}
    assert set(server.routes) == {"/health"}
    parse_tool, parse_options = server.tools["docpipe_parse"]
    rag_tool, rag_options = server.tools["docpipe_rag_query"]
    assert parse_tool.__name__ == "parse_document"
    assert rag_tool.__name__ == "query_documents"
    assert parse_options["annotations"]["readOnlyHint"] is True
    assert rag_options["annotations"]["destructiveHint"] is False
    assert server.options["mask_error_details"] is True


def test_asgi_factory_enables_stateless_http_and_host_origin_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_fastmcp(monkeypatch)

    app = create_mcp_asgi_app(
        object(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        DocpipeSettings(),
        operator_tokens=["x" * 40],
        allowed_hosts=["mcp.example.com"],
        allowed_origins=["https://claude.ai"],
    )

    assert isinstance(app, FakeFastMCP)
    assert app.http_options == {
        "path": "/mcp/",
        "stateless_http": True,
        "host_origin_protection": True,
        "allowed_hosts": ["mcp.example.com"],
        "allowed_origins": ["https://claude.ai"],
    }


@pytest.mark.parametrize(
    ("allowed_hosts", "allowed_origins"),
    [([], []), (["*"], []), (["mcp.example.com"], ["*"])],
)
def test_asgi_factory_rejects_unsafe_host_or_origin_wildcards(
    monkeypatch: pytest.MonkeyPatch,
    allowed_hosts: list[str],
    allowed_origins: list[str],
) -> None:
    _install_fake_fastmcp(monkeypatch)

    with pytest.raises(ConfigurationError):
        create_mcp_asgi_app(
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            DocpipeSettings(),
            operator_tokens=["x" * 40],
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        )
