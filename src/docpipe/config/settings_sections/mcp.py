"""Hosted Model Context Protocol transport settings."""

from pydantic import Field, SecretStr

from docpipe.config.settings_sections.base import Settings


class MCPSettings(Settings):
    """Configuration for the optional operator-authenticated MCP endpoint."""

    mcp_server_enabled: bool = Field(
        default=False, description="Expose the standard Streamable HTTP MCP endpoint at /mcp."
    )
    mcp_operator_tokens: tuple[SecretStr, ...] = Field(
        default_factory=tuple,
        description=(
            "Operator-managed bearer tokens for MCP clients; provide as a JSON list secret."
        ),
    )
    mcp_allowed_hosts: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Exact HTTP Host values trusted by the MCP transport; wildcards are rejected.",
    )
    mcp_allowed_origins: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Exact browser origins allowed by the MCP transport; wildcards are rejected.",
    )
    mcp_tool_timeout_seconds: float = Field(
        default=300.0,
        gt=0,
        le=3600,
        description="Maximum duration in seconds for one MCP tool call.",
    )
    mcp_rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=10_000,
        description="Maximum MCP HTTP POST requests per minute per transport peer.",
    )
    mcp_tenant_id: str | None = Field(
        default=None,
        description=(
            "Operator-assigned tenant scope for MCP bearer clients when tenant policies "
            "are enabled."
        ),
    )
