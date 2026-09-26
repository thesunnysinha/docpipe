"""Outlines adapter for local-model structured extraction."""

from __future__ import annotations

import asyncio
from typing import Any

from docpipe.core.errors import ConfigurationError, ExtractionError, ExtractorNotInstalledError
from docpipe.core.types import ExtractionResult, ExtractionSchema


class OutlinesExtractor:
    """Structured extraction using Outlines (local / self-hosted models)."""

    name = "outlines"
    license = "Apache-2.0"
    requires_gpu = False

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        """Configure a local Outlines model and defer model loading until use.

        Args:
            model: Retained for extractor interface compatibility; the model
                identifier is selected by ``schema.model_id`` at extraction time.
            **kwargs: Options forwarded to Outlines' Transformers model loader.

        Raises:
            ExtractorNotInstalledError: If the optional ``outlines`` package is
                unavailable in the current environment.
        """
        if not self.is_available():
            raise ExtractorNotInstalledError(
                "Outlines is not installed. Install with: pip install docpipe-sdk[outlines]"
            )
        self._model_name = model
        self._kwargs = kwargs
        self._model: Any = None

    def _get_model(self, model_id: str) -> Any:
        if self._model is not None:
            return self._model
        import outlines

        self._model = outlines.models.transformers(model_id, **self._kwargs)
        return self._model

    def extract(
        self,
        text: str,
        schema: ExtractionSchema,
        **kwargs: Any,
    ) -> list[ExtractionResult]:
        """Extract values matching a Pydantic-backed JSON schema.

        Args:
            text: Source text supplied to the model.
            schema: Extraction instructions and output model. ``output_model``
                must be set to a Pydantic class; ``schema.model_id`` identifies
                the local model loaded lazily and then reused by this instance.
            **kwargs: Per-call options passed to the Outlines JSON generator.

        Returns:
            Normalized extraction results produced from the structured output.

        Raises:
            ConfigurationError: If the schema has no Pydantic output model.
            ExtractorNotInstalledError: If Outlines is unavailable.
            ExtractionError: If model generation fails.
        """
        if schema.output_model is None:
            raise ConfigurationError(
                "Outlines extractor requires schema.output_model (a Pydantic model class)."
            )
        try:
            import outlines
        except ImportError as e:
            raise ExtractorNotInstalledError("outlines not installed") from e

        model = self._get_model(schema.model_id)
        generator = outlines.generate.json(model, schema.output_model)
        prompt = f"{schema.description}\n\nText:\n{text}"
        try:
            result = generator(prompt, **kwargs)
        except Exception as e:
            raise ExtractionError(f"Outlines extraction failed: {e}") from e
        return LangChainExtractorShim._to_extraction_results(result)

    async def aextract(
        self,
        text: str,
        schema: ExtractionSchema,
        **kwargs: Any,
    ) -> list[ExtractionResult]:
        """Run synchronous extraction in a worker thread.

        Cancelling the awaiting coroutine does not guarantee that already-started
        model work in the worker thread is interrupted. Exceptions raised by
        :meth:`extract` are propagated to the awaiter.
        """
        return await asyncio.to_thread(self.extract, text, schema, **kwargs)

    @classmethod
    def is_available(cls) -> bool:
        """Return whether the optional Outlines package can import."""
        try:
            import outlines  # noqa: F401

            return True
        except ImportError:
            return False


class LangChainExtractorShim:
    """Reuse result conversion from LangChain extractor."""

    @staticmethod
    def _to_extraction_results(result: Any) -> list[ExtractionResult]:
        from docpipe.extractors.langchain_extractor import LangChainExtractor

        return LangChainExtractor._to_extraction_results(result)
