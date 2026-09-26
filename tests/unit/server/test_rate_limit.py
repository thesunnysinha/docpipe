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


def should_enforce_the_window_and_cap_bucket_cardinality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limit._BUCKETS.clear()
    monkeypatch.setattr(rate_limit, "_MAX_BUCKETS", 1)

    assert rate_limit._check_limit("client-a:/ingest", 1) is None
    assert rate_limit._check_limit("client-a:/ingest", 1) is not None
    assert rate_limit._check_limit("client-b:/ingest", 1) == "Rate limit capacity exceeded."
    assert len(rate_limit._BUCKETS) == 1
