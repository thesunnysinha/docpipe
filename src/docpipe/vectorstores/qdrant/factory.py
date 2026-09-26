"""Construct the optional Qdrant adapter after provider selection."""

from __future__ import annotations

import math

from pydantic import ValidationError
from qdrant_client import AsyncQdrantClient

from docpipe.plugins.configuration import PluginConfig, validation_option_path
from docpipe.plugins.credentials import SecretReference
from docpipe.plugins.errors import PluginConfigurationError
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.vectorstores.qdrant.adapter import QdrantAdapter
from docpipe.vectorstores.qdrant.schemas import QdrantConfig


def create_plugin(config: PluginConfig, *, context: PluginFactoryContext) -> QdrantAdapter:
    """Validate selected options and resolve a secret reference only here."""
    if config.provider != "qdrant":
        raise PluginConfigurationError(
            "Qdrant factory received a different provider", plugin="qdrant"
        )
    options: dict[str, object] = dict(config.options)
    if "api_key" in options:
        raise PluginConfigurationError(
            "Use api_key_ref rather than a literal Qdrant API key",
            plugin="qdrant",
            context={"field": "vector_store.options.api_key"},
        )
    reference_data = options.pop("api_key_ref", None)
    if reference_data is not None:
        if context.credentials is None:
            raise PluginConfigurationError(
                "Qdrant credential resolver is unavailable",
                plugin="qdrant",
                context={"field": "vector_store.options.api_key_ref"},
            )
        try:
            reference = SecretReference.model_validate(reference_data)
        except ValidationError as error:
            raise PluginConfigurationError(
                "Qdrant credential reference is invalid",
                plugin="qdrant",
                context={"field": "vector_store.options.api_key_ref"},
            ) from error
        options["api_key"] = context.credentials.resolve(reference)
    try:
        typed = QdrantConfig.model_validate(options)
    except ValidationError as error:
        raise PluginConfigurationError(
            "Qdrant configuration is invalid",
            plugin="qdrant",
            context={"field": validation_option_path(error, category="vector_store")},
        ) from error
    client = AsyncQdrantClient(
        url=typed.url,
        location=typed.location,
        api_key=typed.api_key.get_secret_value() if typed.api_key else None,
        timeout=math.ceil(typed.timeout_seconds),
        check_compatibility=False,
    )
    return QdrantAdapter(typed, client)
