"""Tests for hybrid capability negotiation."""

import pytest

from docpipe.plugins.contracts.vectorstore import VectorCapability
from docpipe.plugins.errors import PluginCapabilityError
from docpipe.rag.retrieval.base import VectorSearch
from docpipe.rag.retrieval.hybrid import HybridStrategy

from .conftest import EncoderDouble, ReaderDouble


@pytest.mark.asyncio
async def test_hybrid_fails_before_reader_without_negotiated_capability() -> None:
    reader = ReaderDouble()
    search = VectorSearch(
        reader=reader,
        encoder=EncoderDouble(),
        collection="documents",
        capabilities=frozenset({VectorCapability.DENSE_SEARCH}),
        limit=5,
    )

    with pytest.raises(PluginCapabilityError, match="hybrid"):
        await HybridStrategy(search).retrieve("hybrid question")

    assert reader.queries == []


@pytest.mark.asyncio
async def test_hybrid_submits_dense_and_sparse_vectors_when_supported() -> None:
    reader = ReaderDouble()
    search = VectorSearch(
        reader=reader,
        encoder=EncoderDouble(),
        collection="documents",
        capabilities=frozenset({VectorCapability.DENSE_SEARCH, VectorCapability.HYBRID_SEARCH}),
        limit=5,
    )

    await HybridStrategy(search).retrieve("two two terms")

    assert reader.queries[0].dense_vector is not None
    assert reader.queries[0].sparse_vector is not None
