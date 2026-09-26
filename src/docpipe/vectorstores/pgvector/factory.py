"""Typed pgvector plugin construction at the runtime boundary."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import SecretStr, ValidationError

from docpipe.plugins.configuration import PluginConfig, validation_option_path
from docpipe.plugins.credentials import SecretReference
from docpipe.plugins.errors import PluginConfigurationError
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.vectorstores.pgvector.adapter import PgVectorAdapter
from docpipe.vectorstores.pgvector.configuration import PgVectorConfig
from docpipe.vectorstores.pgvector.queries import PsycopgPgVectorRepository


def create_plugin(config: PluginConfig, *, context: PluginFactoryContext) -> PgVectorAdapter:
    """Validate transport options, resolve credentials, and build the adapter."""
    if config.provider != "pgvector":
        raise PluginConfigurationError(
            "pgvector factory received a different provider",
            plugin="pgvector",
        )
    options: dict[str, object] = {key: value for key, value in config.options.items()}
    try:
        dsn = _resolve_dsn(options, context)
        options["dsn"] = dsn
        options.pop("dsn_secret", None)
        typed = PgVectorConfig.model_validate(options)
    except ValidationError as exc:
        raise PluginConfigurationError(
            "pgvector configuration is invalid",
            plugin="pgvector",
            context={"field": validation_option_path(exc, category="vector_store")},
        ) from exc
    except (TypeError, ValueError) as exc:
        if isinstance(exc, PluginConfigurationError):
            raise
        raise PluginConfigurationError(
            "pgvector configuration is invalid",
            plugin="pgvector",
        ) from exc
    repository = PsycopgPgVectorRepository(typed)
    return PgVectorAdapter(typed, repository, context.blocking_runner)


def _resolve_dsn(options: dict[str, object], context: PluginFactoryContext) -> SecretStr:
    literal = options.get("dsn")
    if isinstance(literal, str):
        return SecretStr(literal)
    reference_data = options.get("dsn_secret")
    if not isinstance(reference_data, Mapping):
        raise PluginConfigurationError(
            "pgvector requires a dsn_secret reference",
            plugin="pgvector",
        )
    if context.credentials is None:
        raise PluginConfigurationError(
            "pgvector credential resolver is unavailable",
            plugin="pgvector",
        )
    reference = SecretReference.model_validate(dict(reference_data))
    return context.credentials.resolve(reference)
