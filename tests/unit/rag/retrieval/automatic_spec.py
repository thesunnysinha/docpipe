"""Tests for explicit automatic strategy delegation."""

import pytest

from docpipe.rag.retrieval.automatic import AutomaticStrategy
from docpipe.rag.retrieval.base import RetrievalResult
from docpipe.rag.retrieval.registry import StrategyRegistry

from .conftest import RewriterDouble


class NamedStrategy:
    def __init__(self, name: str) -> None:
        self.name = name
        self.questions: list[str] = []

    async def retrieve(self, question: str) -> RetrievalResult:
        self.questions.append(question)
        return RetrievalResult(())


@pytest.mark.asyncio
async def test_automatic_delegates_known_choice_and_falls_back_to_naive() -> None:
    naive = NamedStrategy("naive")
    hyde = NamedStrategy("hyde")
    registry = StrategyRegistry((naive, hyde))

    selected = await AutomaticStrategy(
        registry,
        RewriterDouble("HYDE"),
        "Choose for {question}",
    ).retrieve("question")
    fallback = await AutomaticStrategy(
        registry,
        RewriterDouble("unsafe-choice"),
        "Choose for {question}",
    ).retrieve("other")

    assert selected.metadata["auto_selected_strategy"] == "hyde"
    assert fallback.metadata["auto_selected_strategy"] == "naive"
    assert hyde.questions == ["question"]
    assert naive.questions == ["other"]
