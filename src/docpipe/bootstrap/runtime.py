"""Application runtime ownership and dependency assembly."""

from __future__ import annotations

import os
from contextlib import AsyncExitStack
from types import TracebackType

from docpipe.config.settings import DocpipeSettings
from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.catalog import PluginCatalog
from docpipe.plugins.credentials import CredentialResolver, EnvironmentCredentialResolver
from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.discovery import discover_plugins
from docpipe.plugins.lifecycle import PluginRuntime
from docpipe.plugins.loader import LoadedPlugin, PluginFactoryContext, PluginLoader
from docpipe.plugins.policy import PluginPolicy
from docpipe.registry.registry import PluginRegistry


class DocpipeRuntime:
    """Owned application dependencies with one explicit async lifecycle."""

    def __init__(
        self,
        *,
        settings: DocpipeSettings,
        catalog: PluginCatalog,
        loader: PluginLoader,
        plugin_runtime: PluginRuntime,
        blocking_runner: BoundedBlockingRunner,
        legacy_registry: PluginRegistry,
        credentials: CredentialResolver | None = None,
    ) -> None:
        self.settings = settings
        self.catalog = catalog
        self.loader = loader
        self.plugin_runtime = plugin_runtime
        self.blocking_runner = blocking_runner
        self.legacy_registry = legacy_registry
        self._credentials = credentials
        self._stack: AsyncExitStack | None = None

    @property
    def is_active(self) -> bool:
        """Return whether owned async resources are active."""
        return self._stack is not None

    async def __aenter__(self) -> DocpipeRuntime:
        """Start plugin and blocking-resource lifecycles."""
        if self._stack is not None:
            raise RuntimeError("Docpipe runtime is already active")
        stack = AsyncExitStack()
        try:
            await stack.enter_async_context(self.plugin_runtime)
            await stack.enter_async_context(self.blocking_runner)
        except BaseException:
            await stack.aclose()
            raise
        self._stack = stack
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """Close owned resources in reverse construction order."""
        stack, self._stack = self._stack, None
        if stack is not None:
            return await stack.__aexit__(exc_type, exc_value, traceback)
        return None

    def factory_context(
        self, *, credentials: CredentialResolver | None = None
    ) -> PluginFactoryContext:
        """Return explicitly scoped services for plugin construction."""
        return PluginFactoryContext(
            blocking_runner=self.blocking_runner,
            credentials=credentials or self._credentials,
        )

    def load_plugin(self, category: PluginCategory, name: str) -> LoadedPlugin[object]:
        """Load a plugin under both process and authenticated tenant policy."""
        from docpipe.profiles.guardrails import catalog_tenant_policy, get_tenant_context

        return self.loader.load(
            category,
            name,
            tenant_policy=catalog_tenant_policy(
                self.settings,
                get_tenant_context(),
            ),
        )


def build_runtime(
    settings: DocpipeSettings,
    *,
    catalog: PluginCatalog | None = None,
    policy: PluginPolicy | None = None,
    plugin_runtime: PluginRuntime | None = None,
    blocking_runner: BoundedBlockingRunner | None = None,
    legacy_registry: PluginRegistry | None = None,
    credentials: CredentialResolver | None = None,
) -> DocpipeRuntime:
    """Compose one isolated runtime from explicit settings and optional doubles."""
    resolved_catalog = catalog or discover_plugins().catalog
    resolved_policy = policy or _policy_from_settings(settings)
    loader = PluginLoader(resolved_catalog, process_policy=resolved_policy)
    return DocpipeRuntime(
        settings=settings,
        catalog=resolved_catalog,
        loader=loader,
        plugin_runtime=plugin_runtime or PluginRuntime(),
        blocking_runner=blocking_runner
        or BoundedBlockingRunner(max_concurrency=settings.max_concurrency),
        legacy_registry=legacy_registry or PluginRegistry(),
        credentials=credentials or EnvironmentCredentialResolver(dict(os.environ)),
    )


def _policy_from_settings(settings: DocpipeSettings) -> PluginPolicy:
    denied = {name.strip() for name in (settings.disabled_plugins or "").split(",") if name.strip()}
    allowlists = {}
    for category, raw in (
        (PluginCategory.SOURCE, settings.enabled_sources),
        (PluginCategory.VECTORSTORE, settings.enabled_vectorstores),
    ):
        if raw is not None:
            allowlists[category] = {name.strip() for name in raw.split(",") if name.strip()}
    return PluginPolicy.create(allowlists=allowlists, denylist=denied)
