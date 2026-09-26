"""Tests for explicit data-driven retrieval strategy selection."""

import pytest

from docpipe.core.errors import RAGError
from docpipe.rag.retrieval.base import RetrievalResult
from docpipe.rag.retrieval.registry import StrategyRegistry


class StrategyDouble:
    name = "naive"

    async def retrieve(self, question: str) -> RetrievalResult:
        return RetrievalResult(())


def test_registry_is_immutable_and_unknown_strategy_fails_precisely() -> None:
    registry = StrategyRegistry((StrategyDouble(),))

    assert registry.require("naive").name == "naive"
    assert registry.names == ("naive",)
    with pytest.raises(RAGError, match="Unknown strategy 'missing'.*naive"):
        registry.require("missing")


def test_registry_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        StrategyRegistry((StrategyDouble(), StrategyDouble()))
