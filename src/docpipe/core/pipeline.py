"""Pipeline orchestrator for parse + extract + ingest."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from docpipe.core.errors import ConfigurationError
from docpipe.core.types import (
    ExtractionResult,
    ExtractionSchema,
    IngestionConfig,
    IngestionResult,
    ParsedDocument,
    PipelineResult,
)

logger = logging.getLogger(__name__)


class Pipeline:
    """Orchestrates document parsing, structured extraction, and optional ingestion."""

    def __init__(
        self,
        parser: str | Any = "docling",
        extractor: str | Any = "langextract",
        ingestion_config: IngestionConfig | None = None,
        parser_options: dict[str, Any] | None = None,
        extractor_options: dict[str, Any] | None = None,
    ) -> None:
        from docpipe.registry.registry import PluginRegistry

        registry = PluginRegistry.get()

        if isinstance(parser, str):
            self._parser = registry.get_parser(parser, **(parser_options or {}))
        else:
            self._parser = parser

        if isinstance(extractor, str):
            self._extractor = registry.get_extractor(extractor, **(extractor_options or {}))
        else:
            self._extractor = extractor

        self._ingestion_config = ingestion_config
        self._ingestion_pipeline: Any = None

    def _get_ingestion_pipeline(self) -> Any:
        """Lazily create ingestion pipeline."""
        if self._ingestion_pipeline is None:
            if self._ingestion_config is None:
                raise ConfigurationError(
                    "Ingestion config not set. Provide ingestion_config to Pipeline."
                )
            from docpipe.ingestion.pipeline import IngestionPipeline

            self._ingestion_pipeline = IngestionPipeline(self._ingestion_config)
        return self._ingestion_pipeline

    def run(self, source: str, schema: ExtractionSchema) -> PipelineResult:
        """Run full pipeline: parse + extract. Optionally ingest if configured."""
        logger.info("Pipeline run: parsing '%s'", source)
        parsed = self._parser.parse(source)

        logger.info("Pipeline run: extracting from parsed text (%d chars)", len(parsed.text))
        extractions = self._extractor.extract(parsed.text, schema)

        result = PipelineResult(
            source=source,
            parsed=parsed,
            extractions=extractions,
        )

        if self._ingestion_config is not None:
            logger.info("Pipeline run: ingesting into '%s'", self._ingestion_config.table_name)
            ingestion = self._get_ingestion_pipeline()
            ingestion.ingest(parsed, extractions=extractions)
            result.metadata["ingestion"] = "completed"

        return result

    async def arun(self, source: str, schema: ExtractionSchema) -> PipelineResult:
        """Async full pipeline."""
        parsed = await self._parser.aparse(source)
        extractions = await self._extractor.aextract(parsed.text, schema)

        result = PipelineResult(
            source=source,
            parsed=parsed,
            extractions=extractions,
        )

        if self._ingestion_config is not None:
            ingestion = self._get_ingestion_pipeline()
            await asyncio.to_thread(ingestion.ingest, parsed, extractions=extractions)
            result.metadata["ingestion"] = "completed"

        return result

    def run_batch(
        self,
        sources: list[str],
        schema: ExtractionSchema,
        max_concurrency: int = 4,
    ) -> list[PipelineResult]:
        """Batch processing with concurrency control."""
        results: list[PipelineResult] = []
        with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
            futures = [executor.submit(self.run, src, schema) for src in sources]
            for future in futures:
                results.append(future.result())
        return results

    def parse_only(self, source: str, **kwargs: Any) -> ParsedDocument:
        """Use just the parser."""
        return self._parser.parse(source, **kwargs)

    def extract_only(
        self, text: str, schema: ExtractionSchema, **kwargs: Any
    ) -> list[ExtractionResult]:
        """Use just the extractor."""
        return self._extractor.extract(text, schema, **kwargs)

    def ingest_only(
        self,
        source: str | ParsedDocument,
        extractions: list[ExtractionResult] | None = None,
    ) -> IngestionResult:
        """Use just the ingestion pipeline."""
        ingestion = self._get_ingestion_pipeline()
        if isinstance(source, str):
            parsed = self._parser.parse(source)
            return ingestion.ingest(parsed, extractions=extractions)
        return ingestion.ingest(source, extractions=extractions)
