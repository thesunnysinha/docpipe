"""Security properties of the expensive-operation rate limiter."""

from __future__ import annotations

import pytest
from starlette.requests import Request

from docpipe.server import rate_limit


def should_key_rate_limits_by_transport_peer_not_identity_headers() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/ingest",
            "headers": [
                (b"authorization", b"Basic attacker-controlled"),
                (b"x-docpipe-tenant-id", b"tenant-controlled"),
            ],
            "client": ("192.0.2.10", 1234),
            "server": ("docpipe", 8000),
            "scheme": "http",
            "query_string": b"",
        }
    )

    assert rate_limit._client_key(request) == "192.0.2.10"


def should_ignore_forwarded_client_address_from_untrusted_peer() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/mcp/",
            "headers": [(b"x-forwarded-for", b"198.51.100.23")],
            "client": ("192.0.2.10", 1234),
            "server": ("docpipe", 8000),
            "scheme": "http",
            "query_string": b"",
        }
    )

    assert rate_limit._client_key(request, trusted_proxy_cidrs=("10.0.0.0/8",)) == "192.0.2.10"


def should_select_first_untrusted_hop_from_right_of_trusted_proxy_chain() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/mcp/",
            "headers": [(b"x-forwarded-for", b"203.0.113.99, 198.51.100.23, 10.0.0.7")],
            "client": ("10.0.0.8", 1234),
            "server": ("docpipe", 8000),
            "scheme": "http",
            "query_string": b"",
        }
    )

    assert rate_limit._client_key(request, trusted_proxy_cidrs=("10.0.0.0/8",)) == "198.51.100.23"


def should_fall_back_to_peer_for_malformed_forwarded_chain() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/mcp/",
            "headers": [(b"x-forwarded-for", b"198.51.100.23, not-an-ip")],
            "client": ("10.0.0.8", 1234),
            "server": ("docpipe", 8000),
            "scheme": "http",
            "query_string": b"",
        }
    )

    assert rate_limit._client_key(request, trusted_proxy_cidrs=("10.0.0.0/8",)) == "10.0.0.8"


def should_enforce_the_window_and_cap_bucket_cardinality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limit._BUCKETS.clear()
    monkeypatch.setattr(rate_limit, "_MAX_BUCKETS", 1)

    assert rate_limit._check_limit("client-a:/ingest", 1) is None
    assert rate_limit._check_limit("client-a:/ingest", 1) is not None
    assert rate_limit._check_limit("client-b:/ingest", 1) == "Rate limit capacity exceeded."
    assert len(rate_limit._BUCKETS) == 1
