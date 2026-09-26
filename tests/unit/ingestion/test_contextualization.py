"""Tests for isolated best-effort contextual chunk injection."""

from __future__ import annotations

import logging

import pytest

from docpipe.ingestion.contextualization import ContextualInjector
from docpipe.ingestion.document_builder import IngestionDocument


class GeneratorDouble:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.full_text = ""

    async def generate(self, full_text: str, chunk_text: str) -> str:
        self.full_text = full_text
        if self.error is not None:
            raise self.error
        return f"Context for {chunk_text}."


@pytest.mark.asyncio
async def test_context_is_prepended_without_mutating_input() -> None:
    generator = GeneratorDouble()
    original = IngestionDocument("record", "chunk", {"source": "document.pdf"}, "document.pdf")

    result = await ContextualInjector(generator, max_document_characters=8).apply(
        (original,),
        "complete document",
    )

    assert result[0].text == "Context for chunk.\n\nchunk"
    assert original.text == "chunk"
    assert generator.full_text == "complete"


@pytest.mark.asyncio
async def test_context_failure_preserves_chunk_and_logs_no_vendor_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    generator = GeneratorDouble(error=RuntimeError("secret prompt content"))
    original = IngestionDocument("record", "chunk", {}, "document.pdf")

    with caplog.at_level(logging.WARNING):
        result = await ContextualInjector(generator).apply((original,), "document")

    assert result == (original,)
    assert "ingestion.contextualization.skipped" in caplog.text
    assert "secret prompt content" not in caplog.text
