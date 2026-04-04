"""LangExtract adapter for structured data extraction."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from docpipe.core.errors import ExtractionError, ExtractorNotInstalledError
from docpipe.core.types import ExtractionResult, ExtractionSchema, SourceSpan

logger = logging.getLogger(__name__)


class LangExtractExtractor:
    """Structured data extractor using Google's LangExtract."""

    name: str = "langextract"

    def __init__(self, **options: Any) -> None:
        if not self.is_available():
            raise ExtractorNotInstalledError(
                "LangExtract is not installed. Install with: pip install docpipe[langextract]"
            )
        self._options = options

    def extract(
        self,
        text: str,
        schema: ExtractionSchema,
        **kwargs: Any,
    ) -> list[ExtractionResult]:
        """Extract structured data using LangExtract."""
        import langextract as lx

        examples = self._build_examples(schema)
        merged_kwargs = {**self._options, **kwargs}

        try:
            raw = lx.extract(
                text=text,
                prompt_description=schema.description,
                examples=examples,
                model_id=schema.model_id,
                **merged_kwargs,
            )
        except Exception as e:
            raise ExtractionError(f"LangExtract extraction failed: {e}") from e

        results: list[ExtractionResult] = []
        for e in raw:
            source_span = None
            if e.char_interval is not None:
                source_span = SourceSpan(start=e.char_interval[0], end=e.char_interval[1])

            results.append(
                ExtractionResult(
                    entity_class=e.extraction_class,
                    text=e.extraction_text,
                    attributes=e.attributes if hasattr(e, "attributes") else {},
                    source_span=source_span,
                )
            )
        return results

    async def aextract(
        self,
        text: str,
        schema: ExtractionSchema,
        **kwargs: Any,
    ) -> list[ExtractionResult]:
        """Async variant - runs sync extract in a thread."""
        return await asyncio.to_thread(self.extract, text, schema, **kwargs)

    @classmethod
    def is_available(cls) -> bool:
        """Check if langextract is installed."""
        try:
            import langextract  # noqa: F401

            return True
        except ImportError:
            return False

    @staticmethod
    def _build_examples(schema: ExtractionSchema) -> list[Any]:
        """Convert schema examples to LangExtract ExampleData objects."""
        if not schema.examples:
            return []

        import langextract as lx

        examples = []
        for ex in schema.examples:
            text = ex.get("text", "")
            extractions = []
            for ext in ex.get("extractions", []):
                extractions.append(
                    lx.Extraction(
                        extraction_class=ext.get("entity_class", ""),
                        extraction_text=ext.get("text", ""),
                        attributes=ext.get("attributes", {}),
                    )
                )
            examples.append(lx.ExampleData(text=text, extractions=extractions))
        return examples
