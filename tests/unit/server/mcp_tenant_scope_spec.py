"""MCP operator-token tenant-boundary configuration tests."""

from __future__ import annotations

import pytest

from docpipe.config.settings import DocpipeSettings
from docpipe.server.app import _validate_mcp_tenant_scope


def test_mcp_tenant_scope_is_optional_without_tenant_configuration() -> None:
    _validate_mcp_tenant_scope(DocpipeSettings())


def test_tenant_mapping_requires_an_explicit_mcp_scope() -> None:
    settings = DocpipeSettings(tenant_identity_map={"alice": "tenant-a"})

    with pytest.raises(ValueError, match="DOCPIPE_MCP_TENANT_ID"):
        _validate_mcp_tenant_scope(settings)


def test_mcp_scope_must_be_an_operator_mapped_tenant() -> None:
    settings = DocpipeSettings(
        tenant_identity_map={"alice": "tenant-a"},
        mcp_tenant_id="tenant-b",
    )

    with pytest.raises(ValueError, match="TENANT_IDENTITY_MAP"):
        _validate_mcp_tenant_scope(settings)


def test_mcp_scope_must_exist_in_plugin_policy_map() -> None:
    settings = DocpipeSettings(
        tenant_plugin_policies='{"tenant-a":{"enabled_parsers":"markitdown"}}',
        mcp_tenant_id="tenant-b",
    )

    with pytest.raises(ValueError, match="TENANT_PLUGIN_POLICIES"):
        _validate_mcp_tenant_scope(settings)


def test_mcp_scope_accepts_configured_tenant() -> None:
    settings = DocpipeSettings(
        tenant_plugin_policies='{"tenant-a":{"enabled_parsers":"markitdown"}}',
        mcp_tenant_id="tenant-a",
    )

    _validate_mcp_tenant_scope(settings)
