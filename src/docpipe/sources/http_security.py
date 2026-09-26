"""HTTP source URL policy and DNS validation at the actual TCP boundary."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol, cast
from urllib.parse import SplitResult, urlsplit, urlunsplit

from docpipe.plugins.errors import SourceAccessError, UnsafeSourceError

HostResolver = Callable[[str, int], Awaitable[tuple[str, ...]]]


@dataclass(frozen=True, slots=True)
class HttpSecurityPolicy:
    """Fail-closed network policy used for every initial URL and redirect."""

    allow_private: bool = False
    allowed_ports: tuple[int, ...] = (80, 443)

    def __post_init__(self) -> None:
        if not self.allowed_ports or any(port < 1 or port > 65535 for port in self.allowed_ports):
            raise ValueError("allowed_ports must contain valid TCP ports")


def inspect_http_url(url: str, policy: HttpSecurityPolicy) -> SplitResult:
    """Reject unsafe URI forms before making an outbound request."""
    try:
        parts = urlsplit(url)
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError as error:
        raise UnsafeSourceError("HTTP source URL is invalid") from error
    if (
        parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
        or port not in policy.allowed_ports
        or any(ord(character) < 32 for character in url)
    ):
        raise UnsafeSourceError("HTTP source URL violates the network policy")
    try:
        address = ipaddress.ip_address(parts.hostname)
    except ValueError:
        if parts.hostname.casefold() == "localhost":
            validate_resolved_addresses(("127.0.0.1",), policy)
    else:
        validate_resolved_addresses((str(address),), policy)
    return parts


def canonical_http_source_id(url: str, policy: HttpSecurityPolicy) -> str:
    """Return a stable HTTP identity with credentials and query data removed."""
    parts = inspect_http_url(url, policy)
    assert parts.hostname is not None
    host = parts.hostname.encode("idna").decode("ascii").casefold()
    authority_host = f"[{host}]" if ":" in host else host
    default_port = 443 if parts.scheme == "https" else 80
    authority = (
        authority_host if parts.port in (None, default_port) else f"{authority_host}:{parts.port}"
    )
    return urlunsplit((parts.scheme, authority, parts.path or "/", "", ""))


def validate_resolved_addresses(
    addresses: Iterable[str], policy: HttpSecurityPolicy
) -> tuple[str, ...]:
    """Require every DNS answer to satisfy the same address policy."""
    vetted: list[str] = []
    for candidate in addresses:
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError as error:
            raise UnsafeSourceError("DNS returned an invalid IP address") from error
        if not policy.allow_private and not address.is_global:
            raise UnsafeSourceError("HTTP source targets a private network address")
        vetted.append(str(address))
    if not vetted:
        raise SourceAccessError("HTTP source hostname did not resolve")
    return tuple(dict.fromkeys(vetted))


async def resolve_host_addresses(host: str, port: int) -> tuple[str, ...]:
    """Resolve all TCP addresses without performing a second lookup at connect."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        try:
            answers = await asyncio.to_thread(socket.getaddrinfo, host, port, 0, socket.SOCK_STREAM)
        except OSError as error:
            raise SourceAccessError("HTTP source hostname could not be resolved") from error
        return tuple(cast(str, answer[4][0]) for answer in answers)
    return (str(address),)


class TcpBackend(Protocol):
    """Narrow HTTP Core TCP connector surface kept inside this integration."""

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> Any:
        """Connect to an already validated literal IP."""
        ...

    async def sleep(self, seconds: float) -> None:
        """Support the core transport's bounded retry machinery."""
        ...


class PinnedNetworkBackend:
    """Resolve, validate every answer, then connect only to a selected literal IP.

    HTTP Core retains the original URL host for HTTP Host and TLS SNI/certificate
    verification; only the socket destination is replaced by the vetted IP.
    Environment proxies are disabled separately by the owning HTTPX client.
    """

    def __init__(
        self,
        backend: TcpBackend,
        policy: HttpSecurityPolicy,
        *,
        resolve_host: HostResolver = resolve_host_addresses,
    ) -> None:
        self._backend = backend
        self._policy = policy
        self._resolve_host = resolve_host

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> Any:
        """Use one validated DNS result, never a second resolver inside TCP."""
        if port not in self._policy.allowed_ports:
            raise UnsafeSourceError("HTTP source TCP port is not permitted")
        addresses = validate_resolved_addresses(await self._resolve_host(host, port), self._policy)
        return await self._backend.connect_tcp(
            addresses[0],
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(self, *args: object, **kwargs: object) -> Any:
        """Reject non-TCP transport paths for externally supplied URLs."""
        raise UnsafeSourceError("HTTP source cannot use local sockets")

    async def sleep(self, seconds: float) -> None:
        await self._backend.sleep(seconds)
