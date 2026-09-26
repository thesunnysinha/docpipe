"""Typed TurboVec plugin construction at the runtime boundary."""

from __future__ import annotations

from pydantic import ValidationError

from docpipe.plugins.configuration import PluginConfig, validation_option_path
from docpipe.plugins.errors import PluginConfigurationError
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.vectorstores.turbovec.adapter import TurboVecAdapter
from docpipe.vectorstores.turbovec.configuration import TurboVecConfig
from docpipe.vectorstores.turbovec.repository import TurboVecFileRepository


def create_plugin(config: PluginConfig, *, context: PluginFactoryContext) -> TurboVecAdapter:
    """Validate options and construct a lazy local TurboVec adapter."""
    if config.provider != "turbovec":
        raise PluginConfigurationError(
            "TurboVec factory received a different provider",
            plugin="turbovec",
        )
    try:
        typed = TurboVecConfig.model_validate(config.options)
    except ValidationError as exc:
        raise PluginConfigurationError(
            "TurboVec configuration is invalid",
            plugin="turbovec",
            context={"field": validation_option_path(exc, category="vector_store")},
        ) from exc
    except (TypeError, ValueError) as exc:
        raise PluginConfigurationError(
            "TurboVec configuration is invalid",
            plugin="turbovec",
        ) from exc
    repository = TurboVecFileRepository(typed)
    return TurboVecAdapter(typed, repository, context.blocking_runner)
