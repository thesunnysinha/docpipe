"""Scheme-based source plugin selection and operation lifecycle ownership."""

from __future__ import annotations

import re
import stat
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from docpipe.bootstrap.runtime import DocpipeRuntime
from docpipe.config.compatibility import resolve_source_options
from docpipe.config.plugin_options import SourcePluginOptions
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.contracts.source import ResolvedSourceHandle, SourceResolver
from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.errors import PluginConfigurationError, UnsupportedSourceError

_PROVIDER_SCHEME = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")


def source_provider(source: str) -> str:
    """Map a user source to a fixed provider name using only its URI scheme."""
    if not source or any(character in source for character in "\x00\r\n"):
        raise UnsupportedSourceError("source is empty or malformed")
    try:
        scheme = urlsplit(source).scheme.casefold()
    except ValueError as error:
        raise UnsupportedSourceError("source URI is malformed") from error
    if scheme in ("", "file"):
        return "local"
    if scheme in ("http", "https"):
        return "http"
    if _PROVIDER_SCHEME.fullmatch(scheme):
        return scheme
    raise UnsupportedSourceError("source scheme is not supported")


class SourceResolverSelector:
    """Load one policy-approved resolver and keep its operation scope alive."""

    def __init__(self, runtime: DocpipeRuntime) -> None:
        self._runtime = runtime

    @asynccontextmanager
    async def resolve(
        self, source: str, *, options: SourcePluginOptions | None = None
    ) -> AsyncIterator[ResolvedSourceHandle]:
        """Resolve a source inside request, plugin, and handle lifecycles.

        The returned handle may be entered by a parser adapter. It is always
        closed before the selected resolver and operation scope are released.
        """
        provider = source_provider(source)
        loaded = self._runtime.load_plugin(PluginCategory.SOURCE, provider)
        resolved = resolve_source_options(provider, self._runtime.settings, namespaced=options)
        if provider == "http":
            root_value = resolved.options["temporary_root"]
            if not isinstance(root_value, str):
                raise PluginConfigurationError(
                    "HTTP source temporary_root must be a path", plugin="http"
                )
            root = _private_temporary_root(Path(root_value))
            config = PluginConfig(
                provider=provider,
                options={**resolved.options, "temporary_root": str(root)},
            )
        else:
            config = resolved
        context = self._runtime.factory_context()
        async with (
            self._runtime.plugin_runtime.request_scope() as request_scope,
            request_scope.operation_scope() as operation_scope,
        ):
            candidate = await operation_scope.acquire(
                f"source.{provider}",
                lambda: loaded.create(config, context=context),
            )
            if not isinstance(candidate, SourceResolver):
                raise TypeError("source plugin must implement SourceResolver")
            if not candidate.supports(source):
                raise UnsupportedSourceError("selected resolver rejected source")
            handle = await candidate.resolve(source)
            try:
                yield handle
            finally:
                await handle.aclose()


def _private_temporary_root(configured: Path) -> Path:
    """Create or validate the application-owned restricted download root."""
    try:
        configured.mkdir(mode=0o700, parents=True, exist_ok=True)
        root = configured.resolve(strict=True)
        mode = root.stat().st_mode
    except (OSError, RuntimeError) as error:
        raise PluginConfigurationError(
            "source temporary root is unavailable", plugin="http"
        ) from error
    if not root.is_dir() or stat.S_IMODE(mode) & 0o077:
        raise PluginConfigurationError(
            "source temporary root permissions are too broad", plugin="http"
        )
    return root
