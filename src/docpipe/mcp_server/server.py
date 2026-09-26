"""FastMCP server construction and HTTP transport assembly."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Any

from docpipe.config.settings import DocpipeSettings
from docpipe.core.errors import ConfigurationError
from docpipe.mcp_server.auth import create_operator_token_verifier
from docpipe.mcp_server.tools import DocpipeMCPTools

if TYPE_CHECKING:
    from docpipe.server.services.documents import DocumentService
    from docpipe.server.services.rag import RAGService

_TOOL_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


def _validate_host_rules(
    allowed_hosts: Sequence[str], allowed_origins: Sequence[str]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Require explicit, non-wildcard transport trust rules for hosted use."""
    hosts = tuple(host.strip() for host in allowed_hosts if host.strip())
    origins = tuple(origin.strip() for origin in allowed_origins if origin.strip())
    if not hosts or any(host == "*" for host in hosts):
        raise ConfigurationError(
            "Hosted MCP requires explicit allowed hostnames; wildcard hosts are not permitted."
        )
    if any(origin == "*" for origin in origins):
        raise ConfigurationError(
            "MCP allowed origins must be explicit; wildcard origins are unsafe."
        )
    return hosts, origins


def create_mcp_server(
    document_service: DocumentService,
    rag_service: RAGService,
    settings: DocpipeSettings,
    *,
    operator_tokens: Iterable[str],
    tool_timeout_seconds: float = 300.0,
    tenant_id: str | None = None,
    name: str = "Docpipe",
) -> Any:
    """Build the injectable FastMCP server and register Docpipe operations.

    This function does not bind a socket or configure a web framework. The
    returned FastMCP instance can be mounted by a host ASGI application or run
    through FastMCP's Streamable HTTP transport.
    """
    try:
        from fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError("Hosted MCP support requires the optional 'fastmcp' package.") from exc
    if tool_timeout_seconds <= 0:
        raise ConfigurationError("MCP tool timeout must be greater than zero.")

    auth = create_operator_token_verifier(operator_tokens)
    server = FastMCP(name, auth=auth, mask_error_details=True)
    tools = DocpipeMCPTools(document_service, rag_service, settings, tenant_id=tenant_id)
    server.tool(
        name="docpipe_parse",
        description=(
            "Parse an operator-approved document path or URL with Docpipe. "
            "Source URL access is constrained by the server's SSRF policy."
        ),
        annotations=_TOOL_ANNOTATIONS,
        timeout=tool_timeout_seconds,
    )(tools.parse_document)
    server.tool(
        name="docpipe_rag_query",
        description=(
            "Answer a question using retrieval-augmented generation over the vector index "
            "configured by the operator. The client cannot supply a database connection or API key."
        ),
        annotations=_TOOL_ANNOTATIONS,
        timeout=tool_timeout_seconds,
    )(tools.query_documents)

    from starlette.responses import JSONResponse

    @server.custom_route("/health", methods=["GET"])
    async def health_check(_: Any) -> JSONResponse:
        """Return liveness only; do not expose deployment configuration."""
        return JSONResponse({"status": "ok"})

    return server


def create_mcp_asgi_app(
    document_service: DocumentService,
    rag_service: RAGService,
    settings: DocpipeSettings,
    *,
    operator_tokens: Iterable[str],
    allowed_hosts: Sequence[str],
    allowed_origins: Sequence[str] = (),
    endpoint_path: str = "/mcp/",
    tool_timeout_seconds: float = 300.0,
    tenant_id: str | None = None,
    name: str = "Docpipe",
) -> Any:
    """Create an authenticated, stateless Streamable HTTP ASGI application.

    Set ``endpoint_path='/'`` when mounting this ASGI app under an outer path
    such as ``/mcp``. When served at the host root, the default endpoint is
    ``/mcp``. FastMCP's own lifespan is attached to the returned app; host
    applications mounting it must compose that lifespan as documented by
    FastMCP.
    """
    hosts, origins = _validate_host_rules(allowed_hosts, allowed_origins)
    server = create_mcp_server(
        document_service,
        rag_service,
        settings,
        operator_tokens=operator_tokens,
        tool_timeout_seconds=tool_timeout_seconds,
        tenant_id=tenant_id,
        name=name,
    )
    return server.http_app(
        path=endpoint_path,
        stateless_http=True,
        host_origin_protection=True,
        allowed_hosts=list(hosts),
        allowed_origins=list(origins),
    )
