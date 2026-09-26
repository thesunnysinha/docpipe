"""Explicit automatic routing across registered retrieval strategies."""

from dataclasses import dataclass

from docpipe.rag.retrieval.base import RetrievalResult, TextRewriter
from docpipe.rag.retrieval.registry import StrategyRegistry


@dataclass(frozen=True, slots=True)
class AutomaticStrategy:
    """Select a known strategy using a constrained text classifier."""

    strategies: StrategyRegistry
    selector: TextRewriter
    prompt: str
    fallback: str = "naive"
    name: str = "auto"

    async def retrieve(self, question: str) -> RetrievalResult:
        """Classify a question, then delegate to a registered strategy.

        A selector response naming this strategy or an unknown strategy uses
        ``fallback``. The selector and chosen strategy errors propagate. Result
        metadata includes the normalized key under ``auto_selected_strategy``.
        """
        raw_choice = await self.selector.complete(self.prompt.format(question=question))
        choice = raw_choice.strip().casefold().replace("-", "_")
        if choice == self.name or choice not in self.strategies.names:
            choice = self.fallback
        result = await self.strategies.require(choice).retrieve(question)
        metadata = dict(result.metadata)
        metadata["auto_selected_strategy"] = choice
        return RetrievalResult(result.chunks, metadata)
