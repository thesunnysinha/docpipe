"""Immutable registry for explicit RAG strategy selection."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from docpipe.core.errors import RAGError
from docpipe.rag.retrieval.base import RetrievalStrategy


class StrategyRegistry:
    """Resolve retrieval strategies by stable, unique names."""

    def __init__(self, strategies: Iterable[RetrievalStrategy]) -> None:
        values: dict[str, RetrievalStrategy] = {}
        for strategy in strategies:
            name = strategy.name.strip().casefold()
            if name in values:
                raise ValueError(f"duplicate retrieval strategy name: {name}")
            values[name] = strategy
        self._strategies: Mapping[str, RetrievalStrategy] = MappingProxyType(values)

    @property
    def names(self) -> tuple[str, ...]:
        """Return registered names in deterministic insertion order."""
        return tuple(self._strategies)

    def require(self, name: str) -> RetrievalStrategy:
        """Return one strategy or raise a precise public error."""
        normalized = name.strip().casefold()
        try:
            return self._strategies[normalized]
        except KeyError as error:
            available = ", ".join(self.names) or "none"
            raise RAGError(
                f"Unknown strategy '{name}'. Available strategies: {available}"
            ) from error
