"""Isolated HTTPX/HTTP Core bridge for connection-time DNS pinning."""

from __future__ import annotations

import ssl
from typing import Any, cast

from docpipe.plugins.errors import PluginDependencyError
from docpipe.sources.http_security import HttpSecurityPolicy, PinnedNetworkBackend


def pinned_async_transport(policy: HttpSecurityPolicy) -> Any:
    """Build the HTTPX transport with a vetted-IP network backend.

    HTTPX does not expose a public DNS pinning hook. This isolated adapter uses
    HTTP Core 1.x's network backend seam, and fails closed if its dependencies
    change. TLS still verifies the original URL hostname, never the pinned IP.
    """
    try:
        import httpcore
        import httpx
        from httpcore._backends.auto import AutoBackend
    except ImportError as error:
        raise PluginDependencyError(
            "HTTP source resolver requires httpx and httpcore 1.x",
            plugin="http",
        ) from error
    if not httpcore.__version__.startswith("1.") or not httpx.__version__.startswith("0.28."):
        raise PluginDependencyError(
            "HTTP source network bridge requires tested HTTPX 0.28 and HTTP Core 1.x",
            plugin="http",
        )

    class PinnedAsyncHTTPTransport(httpx.AsyncHTTPTransport):
        def __init__(self) -> None:
            super().__init__(trust_env=False)
            backend = PinnedNetworkBackend(AutoBackend(), policy)
            ssl_context = ssl.create_default_context()
            pool = httpcore.AsyncConnectionPool(
                ssl_context=ssl_context,
                network_backend=cast(httpcore.AsyncNetworkBackend, backend),
                max_connections=8,
                max_keepalive_connections=4,
            )
            self._pool = pool

    return PinnedAsyncHTTPTransport()
