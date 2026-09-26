"""Policy-gated lazy loading and construction of plugin factories."""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from time import monotonic
from typing import Generic, Protocol, TypeVar, cast

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.api_version import DOCPIPE_PLUGIN_API_VERSION
from docpipe.plugins.catalog import PluginCatalog, PluginRegistration
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.credentials import CredentialResolver
from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.errors import (
    PluginDependencyError,
    PluginError,
    PluginOperationError,
    PluginPolicyError,
)
from docpipe.plugins.policy import PluginPolicy, PolicyReason, evaluate_plugin_policy

_LOGGER = logging.getLogger(__name__)
PluginInstance = TypeVar("PluginInstance")
PluginInstance_co = TypeVar("PluginInstance_co", covariant=True)


class PluginFactory(Protocol[PluginInstance_co]):
    """Typed callable exported by a plugin entry point."""

    def __call__(
        self,
        config: PluginConfig,
        *,
        context: PluginFactoryContext,
    ) -> PluginInstance_co:
        """Construct one configured plugin instance."""
        ...


@dataclass(frozen=True, slots=True)
class PluginFactoryContext:
    """Runtime-owned services available during adapter construction."""

    blocking_runner: BoundedBlockingRunner
    credentials: CredentialResolver | None = None


@dataclass(frozen=True, slots=True)
class LoadedPlugin(Generic[PluginInstance]):
    """Validated registration paired with its imported factory."""

    registration: PluginRegistration
    factory: PluginFactory[PluginInstance]

    def create(
        self,
        config: PluginConfig,
        *,
        context: PluginFactoryContext,
    ) -> PluginInstance:
        """Construct an instance and translate unsafe vendor failures."""
        try:
            return self.factory(config, context=context)
        except PluginError:
            raise
        except Exception as exc:
            raise PluginOperationError(
                "plugin factory failed",
                plugin=self.registration.name,
                context={"category": self.registration.category.value},
            ) from exc


class PluginLoader:
    """Select, authorize, and lazily import plugins from a catalog."""

    def __init__(
        self,
        catalog: PluginCatalog,
        *,
        process_policy: PluginPolicy,
        logger: logging.Logger | None = None,
    ) -> None:
        self._catalog = catalog
        self._process_policy = process_policy
        self._logger = logger or _LOGGER

    @property
    def process_policy(self) -> PluginPolicy:
        """Return the immutable process-level loading policy."""
        return self._process_policy

    def load(
        self,
        category: PluginCategory,
        name: str,
        *,
        tenant_policy: PluginPolicy | None = None,
    ) -> LoadedPlugin[object]:
        """Load a selected factory only after compatibility and policy checks."""
        registration = self._catalog.require(category, name)
        decision = evaluate_plugin_policy(
            registration,
            process=self._process_policy,
            tenant=tenant_policy,
        )
        if (
            decision.reason is PolicyReason.UNAVAILABLE
            and registration.descriptor.unavailable_reason == "missing optional dependency"
        ):
            raise PluginDependencyError(
                "plugin dependency is not installed",
                plugin=name,
                hint=_installation_hint(registration),
                context={"category": category.value, "distribution": registration.distribution},
            )
        if not decision.allowed or not registration.descriptor.supports_api(
            DOCPIPE_PLUGIN_API_VERSION
        ):
            raise PluginPolicyError(
                "plugin is not available under the active policy",
                plugin=name,
                context={"category": category.value, "reason": decision.reason.value},
            )

        started = monotonic()
        self._logger.info(
            "plugin.load.started",
            extra={"event": "plugin.load.started", "plugin": name, "category": category.value},
        )
        try:
            module_name, _, attribute_name = registration.import_target.partition(":")
            module = importlib.import_module(module_name)
            factory_value = getattr(module, attribute_name)
            if not callable(factory_value):
                raise TypeError("plugin entry point is not callable")
            factory = cast(PluginFactory[object], factory_value)
        except (ImportError, AttributeError, TypeError) as exc:
            error = PluginDependencyError(
                "plugin dependency could not be loaded",
                plugin=name,
                hint=_installation_hint(registration),
                context={"category": category.value, "distribution": registration.distribution},
            )
            self._logger.warning(
                "plugin.load.failed",
                extra={"event": "plugin.load.failed", "plugin": name, "error_code": error.code},
            )
            raise error from exc

        self._logger.info(
            "plugin.load.completed",
            extra={
                "event": "plugin.load.completed",
                "plugin": name,
                "category": category.value,
                "duration_ms": round((monotonic() - started) * 1000, 3),
            },
        )
        return LoadedPlugin(registration=registration, factory=factory)


def _installation_hint(registration: PluginRegistration) -> str | None:
    requirement = registration.descriptor.requirement
    if requirement is None:
        return None
    if requirement.extra is not None:
        return f"Install docpipe-sdk[{requirement.extra}]"
    if requirement.package is not None:
        return f"Install {requirement.package}"
    return None
