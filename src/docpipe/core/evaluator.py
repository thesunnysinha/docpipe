"""BaseEvaluator protocol for RAG evaluation plugins."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from docpipe.core.types import EvalConfig, EvalResult


@runtime_checkable
class BaseEvaluator(Protocol):
    """Protocol that all evaluators must implement."""

    name: str

    def evaluate(self, config: EvalConfig) -> EvalResult:
        """Run evaluation and return aggregate metrics."""
        ...

    @classmethod
    def is_available(cls) -> bool:
        """Return True if dependencies are installed."""
        ...
