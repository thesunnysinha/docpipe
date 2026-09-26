"""Parse, extract, and run pipeline operations."""

from __future__ import annotations

from docpipe.bootstrap.runtime import DocpipeRuntime
from docpipe.config.settings import DocpipeSettings
from docpipe.core.pipeline import Pipeline
from docpipe.registry.registry import PluginRegistry
from docpipe.schemas import (
    ExtractRequest,
    ExtractResponse,
    ParseRequest,
    ParseResponse,
    RunRequest,
    RunResponse,
)
from docpipe.server.mappers import extraction_schema_from_request
from docpipe.server.parser_cache import get_cached_parse, store_cached_parse
from docpipe.server.plugin_requests import resolve_fields, resolve_parser_name
from docpipe.sources.parsing import SourceParser


class DocumentService:
    """Serve parsing operations from injected application dependencies."""

    def __init__(
        self,
        settings: DocpipeSettings,
        registry: PluginRegistry,
        runtime: DocpipeRuntime,
    ) -> None:
        """Bind settings, registry, runtime-backed source parsing, and caches."""
        self._settings = settings
        self._registry = registry
        self._source_parser = SourceParser(runtime)

    async def parse(self, req: ParseRequest) -> ParseResponse:
        """Resolve and run a parser, reusing the configured parse cache if present.

        When the configured TTL is positive, parsed results are reused from and
        retained in a process-local cache until expiry; otherwise each request
        parses its source. Misses may fetch or read the source. Response content
        follows the requested text, markdown, or serialized-result format.
        """
        resolved = resolve_fields(
            {"parser": req.parser, "tier": req.tier},
            preset=req.preset,
            applicable={"parser", "tier"},
            explicit=req.model_fields_set,
            endpoint="parse",
        )
        parser_name = resolve_parser_name(resolved, req.source)
        parser = self._registry.get_parser(parser_name)
        cache_ttl = self._settings.parser_cache_ttl_seconds
        parsed = get_cached_parse(req.source, parser_name, ttl_seconds=cache_ttl)
        if parsed is None:
            parsed = await self._source_parser.parse(parser, req.source)
            store_cached_parse(
                req.source,
                parser_name,
                parsed,
                ttl_seconds=cache_ttl,
            )
        result = parsed

        if req.output_format == "markdown":
            content = result.markdown or result.text
        elif req.output_format == "text":
            content = result.text
        else:
            content = result.model_dump_json()

        return ParseResponse(
            source=result.source,
            format=result.format.value,
            content=content,
            metadata=result.metadata,
        )

    async def extract(self, req: ExtractRequest) -> ExtractResponse:
        """Extract fields from validated text using the selected extractor.

        Extraction can invoke the extractor's configured external model provider;
        the service returns extracted values and does not persist them.
        """
        resolved = resolve_fields(
            {"extractor": req.extractor},
            preset=None,
            applicable={"extractor"},
            explicit=req.model_fields_set,
        )
        extractor = self._registry.get_extractor(str(resolved["extractor"]))
        schema = extraction_schema_from_request(req)
        results = await extractor.aextract(req.text, schema)
        return ExtractResponse(extractions=results)

    async def run(self, req: RunRequest) -> RunResponse:
        """Parse a source and extract a schema in one asynchronous pipeline run.

        Parsing may read a local or remote source and the extractor may invoke an
        external provider; the combined result is returned without job persistence.
        """
        schema = extraction_schema_from_request(req)
        pipeline = Pipeline(
            parser=self._registry.get_parser(req.parser),
            extractor=self._registry.get_extractor(req.extractor),
            source_parser=self._source_parser,
        )
        result = await pipeline.arun(req.source, schema)
        return RunResponse.model_validate(result.model_dump())
