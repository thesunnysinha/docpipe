"""Tests for the LangChain embedding boundary adapter."""

from __future__ import annotations

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.embeddings.contracts import EmbeddingEncoder
from docpipe.embeddings.langchain_adapter import LangChainEmbeddingAdapter


class EmbeddingsDouble:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(index), 1.0] for index, _ in enumerate(texts)]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), 2.0]


@pytest.mark.asyncio
async def test_adapter_returns_plain_immutable_vectors() -> None:
    async with BoundedBlockingRunner(max_concurrency=1) as runner:
        adapter = LangChainEmbeddingAdapter(EmbeddingsDouble(), runner)

        documents = await adapter.encode_documents(("one", "two"))
        query = await adapter.encode_query("hello")

    assert isinstance(adapter, EmbeddingEncoder)
    assert documents == ((0.0, 1.0), (1.0, 1.0))
    assert query == (5.0, 2.0)
    assert "langchain" not in type(documents).__module__


def test_public_conformance_helpers_import_without_test_modules() -> None:
    from docpipe.testing.vectorstores import assert_binding_shape

    assert callable(assert_binding_shape)
