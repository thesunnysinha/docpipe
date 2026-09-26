"""Shared vendor-neutral retrieval doubles."""

from __future__ import annotations

import pytest

from docpipe.plugins.contracts.vectorstore import (
    VectorCapability,
    VectorMatch,
    VectorQuery,
)
from docpipe.rag.retrieval.base import VectorSearch


class EncoderDouble:
    async def encode_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple((1.0, 0.0) for _ in texts)

    async def encode_query(self, text: str) -> tuple[float, ...]:
        return (float(len(text)), 1.0)


class ReaderDouble:
    def __init__(self) -> None:
        self.queries: list[VectorQuery] = []
        self.matches: tuple[VectorMatch, ...] = (
            VectorMatch(
                "record-1",
                0.9,
                "relevant text",
                {"source": "report.pdf", "page": 3},
                "report.pdf",
            ),
        )

    async def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]:
        self.queries.append(query)
        return self.matches

    async def aggregate_sources(self, collection: object) -> tuple[object, ...]:
        return ()


class RewriterDouble:
    def __init__(self, result: str) -> None:
        self.result = result
        self.prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.result


@pytest.fixture
def reader() -> ReaderDouble:
    return ReaderDouble()


@pytest.fixture
def search(reader: ReaderDouble) -> VectorSearch:
    return VectorSearch(
        reader=reader,
        encoder=EncoderDouble(),
        collection="documents",
        capabilities=frozenset({VectorCapability.DENSE_SEARCH, VectorCapability.METADATA_FILTER}),
        limit=5,
    )
