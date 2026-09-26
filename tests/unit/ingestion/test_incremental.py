"""Tests for deterministic fingerprints and explicit incremental policy."""

from __future__ import annotations

import logging

import pytest

from docpipe.ingestion.configuration import IncrementalFailureMode
from docpipe.ingestion.incremental import (
    IncrementalDecider,
    IncrementalStateError,
    content_fingerprint,
)


class StateDouble:
    def __init__(self, *, result: bool = False, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    async def contains(self, fingerprint: str) -> bool:
        if self.error is not None:
            raise self.error
        return self.result


def test_fingerprint_uses_raw_bytes_and_canonical_metadata() -> None:
    first = content_fingerprint(b"document bytes", {"page": 1, "kind": "pdf"})
    reordered = content_fingerprint(b"document bytes", {"kind": "pdf", "page": 1})

    assert first == reordered
    assert first != content_fingerprint(b"different bytes", {"kind": "pdf", "page": 1})
    assert first != content_fingerprint(b"document bytes", {"kind": "pdf", "page": 2})


@pytest.mark.asyncio
async def test_lookup_failures_fail_closed_by_default() -> None:
    decider = IncrementalDecider(
        StateDouble(error=RuntimeError("postgresql://admin:secret@db/docpipe")),
        failure_mode=IncrementalFailureMode.FAIL_CLOSED,
    )

    with pytest.raises(IncrementalStateError) as caught:
        await decider.should_skip("fingerprint")

    assert "secret" not in str(caught.value)


@pytest.mark.asyncio
async def test_legacy_best_effort_fails_open_with_safe_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    decider = IncrementalDecider(
        StateDouble(error=RuntimeError("private source content")),
        failure_mode=IncrementalFailureMode.LEGACY_BEST_EFFORT,
    )

    with caplog.at_level(logging.WARNING):
        skipped = await decider.should_skip("fingerprint")

    assert not skipped
    assert "incremental.lookup.failed_open" in caplog.text
    assert "private source content" not in caplog.text
