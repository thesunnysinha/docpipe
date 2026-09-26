"""SDK composition with an isolated default-runtime compatibility hook."""

from __future__ import annotations

from threading import Lock

from docpipe.bootstrap.runtime import DocpipeRuntime, build_runtime
from docpipe.config.loader import load_config
from docpipe.config.settings import DocpipeSettings
from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.catalog import PluginCatalog
from docpipe.plugins.lifecycle import PluginRuntime
from docpipe.plugins.policy import PluginPolicy
from docpipe.registry.registry import PluginRegistry

_DEFAULT_RUNTIME: DocpipeRuntime | None = None
_DEFAULT_RUNTIME_LOCK = Lock()


def create_sdk_runtime(
    settings: DocpipeSettings | None = None,
    *,
    catalog: PluginCatalog | None = None,
    policy: PluginPolicy | None = None,
    plugin_runtime: PluginRuntime | None = None,
    blocking_runner: BoundedBlockingRunner | None = None,
    legacy_registry: PluginRegistry | None = None,
) -> DocpipeRuntime:
    """Build an SDK runtime from explicit settings and optional test doubles."""
    return build_runtime(
        settings or load_config(),
        catalog=catalog,
        policy=policy,
        plugin_runtime=plugin_runtime,
        blocking_runner=blocking_runner,
        legacy_registry=legacy_registry,
    )


def get_default_runtime() -> DocpipeRuntime:
    """Return the process default used only by legacy public entry points."""
    global _DEFAULT_RUNTIME
    with _DEFAULT_RUNTIME_LOCK:
        if _DEFAULT_RUNTIME is None:
            _DEFAULT_RUNTIME = create_sdk_runtime()
        return _DEFAULT_RUNTIME


def reset_default_runtime() -> None:
    """Drop an unstarted compatibility runtime, primarily for legacy tests."""
    global _DEFAULT_RUNTIME
    with _DEFAULT_RUNTIME_LOCK:
        if _DEFAULT_RUNTIME is not None and _DEFAULT_RUNTIME.is_active:
            raise RuntimeError("cannot reset an active default Docpipe runtime")
        _DEFAULT_RUNTIME = None
