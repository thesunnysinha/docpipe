"""EvalPipeline: measure RAG quality via evaluator plugins."""

from __future__ import annotations

import asyncio

from docpipe.core.types import EvalConfig, EvalResult
from docpipe.registry.registry import PluginRegistry


class EvalPipeline:
    """Evaluate RAG quality using registered evaluator plugins."""

    def __init__(self, config: EvalConfig) -> None:
        self._config = config

    def run(self) -> EvalResult:
        """Run evaluation over all questions and compute aggregate metrics."""
        registry = PluginRegistry.get()
        evaluator_name = self._config.evaluator or "builtin"
        evaluator = registry.get_evaluator(evaluator_name)
        return evaluator.evaluate(self._config)

    async def arun(self) -> EvalResult:
        """Async variant."""
        return await asyncio.to_thread(self.run)
