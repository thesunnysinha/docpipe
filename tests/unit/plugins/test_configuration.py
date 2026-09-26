"""Tests for transport-safe plugin configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from docpipe.plugins.configuration import PluginConfig


def test_plugin_config_accepts_recursive_json_values() -> None:
    config = PluginConfig(
        provider="qdrant",
        options={"url": "http://qdrant:6333", "limits": {"batch": 64}, "tls": True},
    )

    assert config.options["limits"] == {"batch": 64}


def test_plugin_config_rejects_python_objects() -> None:
    with pytest.raises(ValidationError):
        PluginConfig(provider="qdrant", options={"client": object()})


def test_plugin_config_is_immutable_and_rejects_unknown_fields() -> None:
    config = PluginConfig(provider="qdrant")
    with pytest.raises(ValidationError):
        config.provider = "pgvector"
    with pytest.raises(ValidationError):
        PluginConfig(provider="qdrant", unexpected=True)  # type: ignore[call-arg]
