"""Tests for scoped secret references and credential resolution."""

from __future__ import annotations

import pytest

from docpipe.plugins.credentials import (
    EnvironmentCredentialResolver,
    SecretReference,
)
from docpipe.plugins.errors import PluginConfigurationError


def test_secret_reference_does_not_render_resolved_value() -> None:
    reference = SecretReference(kind="environment", name="QDRANT_API_KEY")

    assert "secret" not in repr(reference)
    assert reference.model_dump() == {"kind": "environment", "name": "QDRANT_API_KEY"}


def test_environment_resolver_returns_masked_secret() -> None:
    resolver = EnvironmentCredentialResolver({"QDRANT_API_KEY": "secret-value"})

    secret = resolver.resolve(SecretReference(kind="environment", name="QDRANT_API_KEY"))

    assert str(secret) == "**********"
    assert secret.get_secret_value() == "secret-value"


def test_environment_resolver_rejects_missing_secret() -> None:
    resolver = EnvironmentCredentialResolver({})

    with pytest.raises(PluginConfigurationError, match="QDRANT_API_KEY"):
        resolver.resolve(SecretReference(kind="environment", name="QDRANT_API_KEY"))
