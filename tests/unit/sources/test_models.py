"""Immutable source identity and byte metadata."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from docpipe.plugins.contracts.source import SourceDescriptor


def test_source_descriptor_normalizes_identity_and_detaches_metadata() -> None:
    metadata: dict[str, object] = {"kind": "report"}
    descriptor = SourceDescriptor(
        source_id=" file:///documents/report.pdf ",
        display_name=" report.pdf ",
        media_type="Application/PDF",
        content_length=12,
        version_token=" v1 ",
        content_fingerprint="sha256:" + "a" * 64,
        metadata=metadata,
    )
    metadata["kind"] = "changed"

    assert descriptor.source_id == "file:///documents/report.pdf"
    assert descriptor.display_name == "report.pdf"
    assert descriptor.media_type == "application/pdf"
    assert descriptor.version_token == "v1"
    assert descriptor.metadata["kind"] == "report"
    with pytest.raises((FrozenInstanceError, AttributeError)):
        descriptor.content_length = 4  # type: ignore[misc]
    with pytest.raises(TypeError):
        descriptor.metadata["kind"] = "changed"  # type: ignore[index]


@pytest.mark.parametrize("source_id", ["", "  ", "http://host/path?token=secret", "\x00bad"])
def test_identity_rejects_unsafe_or_empty_ids(source_id: str) -> None:
    with pytest.raises(ValueError):
        SourceDescriptor(source_id=source_id, display_name="document")


def test_invalid_content_fingerprint_and_length_are_rejected() -> None:
    with pytest.raises(ValueError):
        SourceDescriptor("file:///report", "report", content_length=-1)
    with pytest.raises(ValueError):
        SourceDescriptor("file:///report", "report", content_fingerprint="etag-123")
