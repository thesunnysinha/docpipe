"""Operator bearer-token verifier tests."""

from __future__ import annotations

import asyncio
import sys
import types
from dataclasses import dataclass
from typing import Any

import pytest

from docpipe.core.errors import ConfigurationError
from docpipe.mcp_server.auth import (
    _matches_configured_token,
    create_operator_token_verifier,
    validate_operator_tokens,
)

TOKEN_A = "a" * 40
TOKEN_B = "b" * 40


def test_validate_operator_tokens_hashes_tokens_without_retaining_plaintext() -> None:
    digests = validate_operator_tokens([TOKEN_A, TOKEN_B])

    assert len(digests) == 2
    assert all(len(digest) == 32 for digest in digests)
    assert TOKEN_A.encode() not in digests
    assert _matches_configured_token(TOKEN_A, digests)
    assert not _matches_configured_token("c" * 40, digests)


@pytest.mark.parametrize("tokens", [[], ["short"], [""], [None]])
def test_validate_operator_tokens_rejects_empty_or_weak_values(tokens: list[Any]) -> None:
    with pytest.raises(ConfigurationError):
        validate_operator_tokens(tokens)


def _install_fake_fastmcp_auth(monkeypatch: pytest.MonkeyPatch) -> type:
    """Install the narrow FastMCP auth interface used by the optional adapter."""

    class TokenVerifier:
        def __init__(self) -> None:
            self.required_scopes: list[str] = []

    @dataclass
    class AccessToken:
        token: str
        client_id: str
        scopes: list[str]
        claims: dict[str, Any]

    package = types.ModuleType("fastmcp")
    package.__path__ = []  # type: ignore[attr-defined]
    server_package = types.ModuleType("fastmcp.server")
    server_package.__path__ = []  # type: ignore[attr-defined]
    auth_module = types.ModuleType("fastmcp.server.auth")
    auth_module.TokenVerifier = TokenVerifier  # type: ignore[attr-defined]
    auth_module.AccessToken = AccessToken  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fastmcp", package)
    monkeypatch.setitem(sys.modules, "fastmcp.server", server_package)
    monkeypatch.setitem(sys.modules, "fastmcp.server.auth", auth_module)
    return AccessToken


def test_operator_verifier_accepts_tokens_and_returns_safe_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access_token_type = _install_fake_fastmcp_auth(monkeypatch)
    verifier = create_operator_token_verifier([TOKEN_A, TOKEN_B])

    accepted = asyncio.run(verifier.verify_token(TOKEN_B))  # type: ignore[attr-defined]
    rejected = asyncio.run(verifier.verify_token("x" * 40))  # type: ignore[attr-defined]

    assert isinstance(accepted, access_token_type)
    assert accepted.client_id == "docpipe-operator"
    assert accepted.claims == {"sub": "docpipe-operator"}
    assert rejected is None
