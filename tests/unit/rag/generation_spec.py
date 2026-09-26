"""Tests for retrieval-independent generation helpers."""

from docpipe.core.types import RAGChunk
from docpipe.rag.generation import build_context, normalize_content


def test_context_contains_stable_citations_and_pages() -> None:
    context = build_context(
        (
            RAGChunk(content="first", score=0.9, source="a.pdf", page=2),
            RAGChunk(content="second", score=0.8, source="b.pdf"),
        )
    )

    assert "[1] (Source: a.pdf, page 2)\nfirst" in context
    assert "[2] (Source: b.pdf)\nsecond" in context


def test_stream_content_normalizes_provider_block_shapes() -> None:
    assert normalize_content("plain") == "plain"
    assert normalize_content([{"text": "first"}, {"content": " second"}]) == "first second"
    assert normalize_content(None) == ""
