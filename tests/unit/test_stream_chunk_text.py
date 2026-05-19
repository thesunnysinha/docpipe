"""Tests for LangChain stream chunk normalization."""

from docpipe.rag.pipeline import _stream_chunk_to_text


def test_stream_chunk_plain_string() -> None:
    assert _stream_chunk_to_text("hello") == "hello"


def test_stream_chunk_gemini_blocks() -> None:
    blocks = [{"type": "text", "text": "Hello"}, {"type": "text", "text": " world"}]
    assert _stream_chunk_to_text(blocks) == "Hello world"


def test_stream_chunk_empty() -> None:
    assert _stream_chunk_to_text(None) == ""
    assert _stream_chunk_to_text([]) == ""
