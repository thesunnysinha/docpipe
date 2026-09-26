"""Tenant policy identity must come from authenticated operator mapping."""

from __future__ import annotations

from secrets import token_urlsafe

from fastapi.testclient import TestClient

from docpipe.config.settings import DocpipeSettings
from docpipe.profiles.guardrails import enabled_plugins, reset_tenant_context, set_tenant_context
from docpipe.server.app import create_app

_TEST_PASSWORD = token_urlsafe(32)


def _settings() -> DocpipeSettings:
    return DocpipeSettings(
        auth_enabled=True,
        username="trusted-user",
        password=_TEST_PASSWORD,
        tenant_identity_map={"trusted-user": "tenant-a"},
        tenant_plugin_policies=(
            '{"tenant-a":{"enabled_sources":"local"},"tenant-b":{"enabled_sources":"http"}}'
        ),
    )


def should_ignore_caller_tenant_header_and_use_authenticated_mapping() -> None:
    with TestClient(create_app(_settings())) as client:
        response = client.get(
            "/plugins",
            auth=("trusted-user", _TEST_PASSWORD),
            headers={"X-Docpipe-Tenant-Id": "tenant-b"},
        )

    assert response.status_code == 200
    catalog = response.json()["catalog"]["source"]
    assert catalog["local"]["allowed"] is True
    assert catalog["http"]["allowed"] is False


def should_deny_authenticated_user_without_an_explicit_tenant_mapping() -> None:
    settings = _settings().model_copy(update={"tenant_identity_map": {}})
    with TestClient(create_app(settings)) as client:
        response = client.get("/plugins", auth=("trusted-user", _TEST_PASSWORD))

    assert response.status_code == 403


def should_not_start_authenticated_server_with_an_empty_password() -> None:
    from docpipe.bootstrap.server import _validate_server_security

    settings = DocpipeSettings(auth_enabled=True, password="")

    try:
        _validate_server_security(settings)
    except RuntimeError as error:
        assert "DOCPIPE_PASSWORD" in str(error)
    else:
        raise AssertionError("server accepted enabled authentication without a password")


def should_apply_explicit_app_settings_to_legacy_plugin_allowlists() -> None:
    settings = DocpipeSettings(
        enabled_parsers="legacy-parser",
        tenant_plugin_policies='{"tenant-a":{"enabled_parsers":"tenant-parser"}}',
    )
    tokens = set_tenant_context("tenant-a", settings=settings)
    try:
        assert enabled_plugins("parsers") == ["tenant-parser"]
    finally:
        reset_tenant_context(tokens)
