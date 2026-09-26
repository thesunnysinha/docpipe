"""Operator-managed bearer-token verification for hosted MCP deployments."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterable
from typing import Any

from docpipe.core.errors import ConfigurationError

_MINIMUM_TOKEN_LENGTH = 32


def _token_digest(token: str) -> bytes:
    """Return a fixed-length digest so token comparisons are constant-time."""
    return hashlib.sha256(token.encode("utf-8")).digest()


def validate_operator_tokens(tokens: Iterable[str]) -> tuple[bytes, ...]:
    """Validate and hash operator-provided bearer secrets.

    Raw tokens are intentionally not retained by the returned verifier. Callers
    should supply high-entropy secrets through a secret manager or environment.
    """
    digests: list[bytes] = []
    for token in tokens:
        if not isinstance(token, str) or len(token) < _MINIMUM_TOKEN_LENGTH:
            raise ConfigurationError(
                "MCP operator bearer tokens must be strings of at least 32 characters."
            )
        digests.append(_token_digest(token))
    if not digests:
        raise ConfigurationError("At least one MCP operator bearer token is required.")
    return tuple(digests)


def _matches_configured_token(token: str, expected_digests: tuple[bytes, ...]) -> bool:
    """Compare one supplied credential against every configured token digest."""
    if not isinstance(token, str) or not token:
        return False
    supplied_digest = _token_digest(token)
    matched = False
    for expected_digest in expected_digests:
        matched = hmac.compare_digest(supplied_digest, expected_digest) | matched
    return matched


def create_operator_token_verifier(tokens: Iterable[str]) -> Any:
    """Create a FastMCP token verifier without retaining plaintext credentials.

    FastMCP is an optional dependency, so its auth classes are imported only
    when the hosted MCP feature is actually configured.
    """
    try:
        from fastmcp.server.auth import AccessToken, TokenVerifier
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError("Hosted MCP support requires the optional 'fastmcp' package.") from exc

    expected_digests = validate_operator_tokens(tokens)

    class OperatorTokenVerifier(TokenVerifier):
        """Accept configured operator tokens using fixed-time digest checks."""

        async def verify_token(self, token: str) -> AccessToken | None:
            if not _matches_configured_token(token, expected_digests):
                return None
            return AccessToken(
                token=token,
                client_id="docpipe-operator",
                scopes=["docpipe"],
                claims={"sub": "docpipe-operator"},
            )

    return OperatorTokenVerifier()
