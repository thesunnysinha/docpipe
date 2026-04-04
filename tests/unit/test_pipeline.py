"""Tests for the pipeline orchestrator."""

import pytest

from docpipe.core.pipeline import Pipeline
from docpipe.core.types import ExtractionSchema
from docpipe.registry.registry import PluginRegistry
from tests.conftest import MockExtractor, MockParser


@pytest.fixture
def _register_mocks():
    registry = PluginRegistry.get()
    registry.register_parser("mock", MockParser)
    registry.register_extractor("mock", MockExtractor)


@pytest.mark.usefixtures("_register_mocks")
class TestPipeline:
    def test_run(self, sample_schema: ExtractionSchema):
        pipeline = Pipeline(parser="mock", extractor="mock")
        result = pipeline.run("test.pdf", sample_schema)

        assert result.source == "test.pdf"
        assert result.parsed.text == "Parsed content of test.pdf"
        assert len(result.extractions) == 1
        assert result.extractions[0].entity_class == "mock_entity"

    def test_parse_only(self):
        pipeline = Pipeline(parser="mock", extractor="mock")
        parsed = pipeline.parse_only("test.pdf")

        assert parsed.source == "test.pdf"
        assert "Parsed content" in parsed.text

    def test_extract_only(self, sample_schema: ExtractionSchema):
        pipeline = Pipeline(parser="mock", extractor="mock")
        results = pipeline.extract_only("some text", sample_schema)

        assert len(results) == 1
        assert results[0].entity_class == "mock_entity"

    def test_run_batch(self, sample_schema: ExtractionSchema):
        pipeline = Pipeline(parser="mock", extractor="mock")
        results = pipeline.run_batch(["a.pdf", "b.pdf"], sample_schema, max_concurrency=2)

        assert len(results) == 2
        assert results[0].source == "a.pdf"
        assert results[1].source == "b.pdf"

    def test_with_parser_instance(self, sample_schema: ExtractionSchema):
        pipeline = Pipeline(parser=MockParser(), extractor=MockExtractor())
        result = pipeline.run("test.pdf", sample_schema)

        assert result.source == "test.pdf"

    @pytest.mark.asyncio
    async def test_arun(self, sample_schema: ExtractionSchema):
        pipeline = Pipeline(parser="mock", extractor="mock")
        result = await pipeline.arun("test.pdf", sample_schema)

        assert result.source == "test.pdf"
        assert len(result.extractions) == 1
