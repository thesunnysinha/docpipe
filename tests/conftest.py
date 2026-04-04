"""Shared test fixtures."""

from __future__ import annotations

from typing import Any

import pytest

from docpipe.core.types import (
    DocumentFormat,
    ExtractionResult,
    ExtractionSchema,
    ParsedDocument,
    SourceSpan,
)
from docpipe.registry.registry import PluginRegistry


@pytest.fixture(autouse=True)
def _reset_registry():
    """Reset the plugin registry before each test."""
    PluginRegistry.reset()
    yield
    PluginRegistry.reset()


class MockParser:
    """Mock parser for testing."""

    name: str = "mock"

    def __init__(self, **kwargs: Any) -> None:
        self._options = kwargs

    def parse(self, source: str, **kwargs: Any) -> ParsedDocument:
        return ParsedDocument(
            source=source,
            format=DocumentFormat.TEXT,
            text=f"Parsed content of {source}",
            markdown=f"# Parsed\n\nContent of {source}",
            metadata={"mock": True},
        )

    async def aparse(self, source: str, **kwargs: Any) -> ParsedDocument:
        return self.parse(source, **kwargs)

    def parse_batch(self, sources: list[str], **kwargs: Any) -> list[ParsedDocument]:
        return [self.parse(s, **kwargs) for s in sources]

    @classmethod
    def is_available(cls) -> bool:
        return True

    @classmethod
    def supported_formats(cls) -> list[str]:
        return ["text"]


class MockExtractor:
    """Mock extractor for testing."""

    name: str = "mock"

    def __init__(self, **kwargs: Any) -> None:
        self._options = kwargs

    def extract(
        self, text: str, schema: ExtractionSchema, **kwargs: Any
    ) -> list[ExtractionResult]:
        return [
            ExtractionResult(
                entity_class="mock_entity",
                text="mock extraction",
                attributes={"from": "mock"},
                source_span=SourceSpan(start=0, end=4),
            )
        ]

    async def aextract(
        self, text: str, schema: ExtractionSchema, **kwargs: Any
    ) -> list[ExtractionResult]:
        return self.extract(text, schema, **kwargs)

    @classmethod
    def is_available(cls) -> bool:
        return True


@pytest.fixture
def mock_parser() -> MockParser:
    return MockParser()


@pytest.fixture
def mock_extractor() -> MockExtractor:
    return MockExtractor()


@pytest.fixture
def sample_schema() -> ExtractionSchema:
    return ExtractionSchema(
        description="Extract people and their ages",
        model_id="test-model",
        entity_classes=["person"],
        examples=[
            {
                "text": "John is 30 years old.",
                "extractions": [
                    {
                        "entity_class": "person",
                        "text": "John",
                        "attributes": {"age": 30},
                    }
                ],
            }
        ],
    )
