"""Answer-generation ports and provider-neutral content helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol

from docpipe.core.types import RAGChunk, TokenUsage


@dataclass(frozen=True, slots=True)
class GeneratedAnswer:
    """Normalized output returned by an answer generator."""

    answer: str
    structured: Any = None
    usage: TokenUsage | None = None


class AnswerGenerator(Protocol):
    """Generate a grounded answer from a question and prepared context."""

    async def generate(self, question: str, context: str) -> GeneratedAnswer:
        """Return normalized text, structured output, and token usage."""
        ...


class StreamingAnswerGenerator(AnswerGenerator, Protocol):
    """Answer generator that can emit provider-independent text fragments."""

    def stream(self, question: str, context: str) -> AsyncIterator[str]:
        """Return an asynchronous iterator of text fragments."""
        ...


def build_context(chunks: tuple[RAGChunk, ...]) -> str:
    """Render chunks with stable, one-based source citations."""
    sections: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        page = f", page {chunk.page}" if chunk.page is not None else ""
        sections.append(f"[{index}] (Source: {chunk.source}{page})\n{chunk.content}")
    return "\n\n".join(sections)


def normalize_content(content: object) -> str:
    """Normalize common provider response block shapes into plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                value = block.get("text") or block.get("content")
                if value is not None:
                    parts.append(str(value))
        return "".join(parts)
    return str(content)


# Keep vendor integration in its own small module; the integration itself
# performs all optional imports only when model generation is selected.
from docpipe.rag.generation_langchain import LangChainAnswerGenerator  # noqa: E402

__all__ = [
    "AnswerGenerator",
    "GeneratedAnswer",
    "LangChainAnswerGenerator",
    "StreamingAnswerGenerator",
    "build_context",
    "normalize_content",
]
