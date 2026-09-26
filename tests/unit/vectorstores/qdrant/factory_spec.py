"""Qdrant factory validates only after selection and resolves references safely."""

from __future__ import annotations

import pytest

pytest.importorskip("qdrant_client")

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.credentials import EnvironmentCredentialResolver
from docpipe.plugins.errors import PluginConfigurationError
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.vectorstores.qdrant.factory import create_plugin


def should_report_nested_unknown_option_without_value() -> None:
    with pytest.raises(PluginConfigurationError) as failure:
        create_plugin(
            PluginConfig(
                provider="qdrant",
                options={"location": ":memory:", "unknown_option": "private-value"},
            ),
            context=PluginFactoryContext(blocking_runner=BoundedBlockingRunner(1)),
        )

    assert failure.value.context["field"] == "vector_store.options.unknown_option"
    assert "private-value" not in str(failure.value)


def should_resolve_environment_key_without_serializing_secret() -> None:
    config = PluginConfig(
        provider="qdrant",
        options={
            "url": "https://vectors.example",
            "collection": "docs",
            "api_key_ref": {"kind": "environment", "name": "QDRANT_KEY"},
        },
    )
    plugin = create_plugin(
        config,
        context=PluginFactoryContext(
            blocking_runner=BoundedBlockingRunner(1),
            credentials=EnvironmentCredentialResolver({"QDRANT_KEY": "private-value"}),
        ),
    )

    assert "private-value" not in config.model_dump_json()
    assert "private-value" not in repr(plugin._config)


def should_reject_literal_api_key() -> None:
    with pytest.raises(PluginConfigurationError, match="api_key_ref"):
        create_plugin(
            PluginConfig(provider="qdrant", options={"location": ":memory:", "api_key": "secret"}),
            context=PluginFactoryContext(blocking_runner=BoundedBlockingRunner(1)),
        )
