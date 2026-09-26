"""Immutable normalized metadata for a resolved document source."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from docpipe.plugins.contracts.vectorstore.values import FrozenJson, freeze_metadata

_FINGERPRINT = re.compile(r"sha256:[0-9a-f]{64}")
_MEDIA_TYPE = re.compile(r"[a-z0-9][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]*")


def is_valid_media_type(value: str) -> bool:
    """Return whether ``value`` is a normalized, metadata-safe MIME type."""
    return _MEDIA_TYPE.fullmatch(value.strip().casefold()) is not None


@dataclass(frozen=True, slots=True)
class SourceDescriptor:
    """Normalized source identity, content properties, and trusted fingerprint.

    ``version_token`` is an opaque provider hint, never proof of content bytes.
    ``content_fingerprint`` is a cryptographic SHA-256 digest of verified bytes.
    The URI identity belongs in results, while event logs use an opaque ID.
    """

    source_id: str
    display_name: str
    media_type: str = "application/octet-stream"
    content_length: int | None = None
    version_token: str | None = None
    content_fingerprint: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        source_id = self.source_id.strip()
        display_name = self.display_name.strip()
        media_type = self.media_type.strip().casefold()
        token = self.version_token.strip() if self.version_token is not None else None
        if not source_id or any(character in source_id for character in "?#\x00\r\n"):
            raise ValueError("source_id must not contain a query or control characters")
        if not display_name or any(character in display_name for character in "/\\\x00\r\n"):
            raise ValueError("display_name must be a safe basename")
        if not is_valid_media_type(media_type):
            raise ValueError("media_type must be a safe MIME type")
        if self.content_length is not None and self.content_length < 0:
            raise ValueError("content_length must be non-negative")
        if token == "" or (token is not None and any(c in token for c in "\x00\r\n")):
            raise ValueError("version_token must not contain control characters")
        if self.content_fingerprint is not None and not _FINGERPRINT.fullmatch(
            self.content_fingerprint
        ):
            raise ValueError("content_fingerprint must be a SHA-256 byte digest")
        frozen: Mapping[str, FrozenJson] = freeze_metadata(self.metadata)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "media_type", media_type)
        object.__setattr__(self, "version_token", token)
        object.__setattr__(self, "metadata", frozen)
