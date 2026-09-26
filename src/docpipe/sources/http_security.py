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
    """Fail-closed network policy applied to HTTP sources and redirects.

    Private, loopback, link-local, and other non-global destinations are
    rejected unless ``allow_private`` is explicitly enabled. Port checks apply
    both to parsed URLs and to the TCP connection attempt; enabling private
    addresses does not bypass scheme, credential, or port validation.

    Args:
        allow_private: Whether non-global IP destinations are allowed. Keep
            this false for deployments that accept untrusted URLs.
        allowed_ports: Non-empty set of TCP destination ports. Defaults to
            standard HTTP and HTTPS ports.

    Raises:
        ValueError: If the allowed-port collection is empty or contains an
            invalid TCP port.
    """

    allow_private: bool = False
    allowed_ports: tuple[int, ...] = (80, 443)

    def __post_init__(self) -> None:
        """Reject invalid port policies at configuration construction time."""
        if not self.allowed_ports or any(port < 1 or port > 65535 for port in self.allowed_ports):
            raise ValueError("allowed_ports must contain valid TCP ports")


def inspect_http_url(url: str, policy: HttpSecurityPolicy) -> SplitResult:
    """Validate URL syntax and literal-IP policy before any network I/O.

    This function does not resolve ordinary hostnames. Their complete DNS
    answer set must be checked by :func:`validate_resolved_addresses` at the
    transport boundary, immediately before connecting. URL credentials,
    non-empty fragments, control characters, non-HTTP schemes, and disallowed ports are
    rejected; ``localhost`` is checked as loopback even before DNS resolution.

    Args:
        url: Untrusted absolute HTTP(S) URL.
        policy: Address and port policy to enforce.

    Returns:
        Parsed URL components after syntax, scheme, and literal-address checks.

    Raises:
        UnsafeSourceError: If the URL violates policy or is malformed.
    """
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
    """Build a normalized, non-secret identifier for an HTTP source URL.

    Hostnames are IDNA-normalized and case-folded, default ports are omitted,
    and an empty path becomes ``/``. Query strings and fragments are excluded
    so credentials or signed query parameters are not copied into source IDs;
    callers must not treat the resulting ID as proof that two responses have
    identical content.

    Args:
        url: Candidate URL, validated under the same policy as retrieval.
        policy: Address and port policy used for URL validation.

    Returns:
        Canonical scheme/authority/path identifier without query or fragment.

    Raises:
        UnsafeSourceError: If URL syntax or policy validation fails.
    """
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
    """Validate and deduplicate every IP address returned for a host.

    Checking every answer prevents a hostname with a mixture of public and
    private records from being accepted based only on resolver order. Results
    preserve first-seen order so the transport can connect to a validated
    literal address without performing another DNS lookup.

    Args:
        addresses: IP address strings returned by a resolver.
        policy: Address policy; when private access is disabled, only globally
            routable addresses are accepted.

    Returns:
        Unique canonical IP strings in their original order.

    Raises:
        UnsafeSourceError: If an answer is malformed or disallowed by policy.
        SourceAccessError: If the resolver returned no addresses.
    """
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
    """Resolve a host to all candidate TCP IPs using the system resolver.

    Literal IP inputs bypass DNS. Hostname resolution runs in a worker thread
    to avoid blocking the event loop; the returned candidates are not trusted
    until validated against policy and pinned by :class:`PinnedNetworkBackend`.

    Args:
        host: Hostname or literal IP from an inspected HTTP(S) URL.
        port: Destination TCP port supplied to the system resolver.

    Returns:
        All resolved IP strings, possibly containing duplicates that a later
        validation step removes.

    Raises:
        SourceAccessError: If DNS resolution fails.
    """
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
        """Wrap a backend with policy validation and a controlled resolver.

        Args:
            backend: HTTP Core connector used only after an address is vetted.
            policy: Port/address restrictions applied at connect time.
            resolve_host: Injectable asynchronous resolver, useful for tests
                and controlled runtime integrations.
        """
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
        """Validate all DNS answers and connect to one literal vetted address.

        The original hostname remains available to HTTP Core for TLS SNI,
        certificate verification, and the HTTP Host header; only the socket
        destination is pinned to the selected IP. This prevents a second DNS
        lookup inside the TCP connector from rebinding the destination.

        Raises:
            UnsafeSourceError: If the port or any resolved address violates
                the configured policy.
            SourceAccessError: If hostname resolution yields no usable address.
        """
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
        """Reject local-socket paths that bypass URL host validation.

        Raises:
            UnsafeSourceError: Always, because externally supplied HTTP(S)
                sources must use the vetted TCP path.
        """
        raise UnsafeSourceError("HTTP source cannot use local sockets")

    async def sleep(self, seconds: float) -> None:
        """Delegate bounded retry delays to the wrapped HTTP Core backend."""
        await self._backend.sleep(seconds)
