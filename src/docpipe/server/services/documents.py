"""Parse, extract, and run pipeline operations."""

from __future__ import annotations

from docpipe.config import get_settings
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


class DocumentService:
    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    async def parse(self, req: ParseRequest) -> ParseResponse:
        resolved = resolve_fields(
            {"parser": req.parser, "tier": req.tier},
            preset=req.preset,
            applicable={"parser", "tier"},
            explicit=req.model_fields_set,
            endpoint="parse",
        )
        parser_name = resolve_parser_name(resolved, req.source)
        parser = self._registry.get_parser(parser_name)
        settings = get_settings()
        cache_ttl = settings.parser_cache_ttl_seconds
        parsed = get_cached_parse(req.source, parser_name, ttl_seconds=cache_ttl)
        if parsed is None:
            parsed = await parser.aparse(req.source)
            store_cached_parse(
                req.source,
                parser_name,
                parsed,
                ttl_seconds=settings.parser_cache_ttl_seconds,
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
        """Parse and extract in a single pipeline invocation."""
        schema = extraction_schema_from_request(req)
        pipeline = Pipeline(parser=req.parser, extractor=req.extractor)
        result = await pipeline.arun(req.source, schema)
        return RunResponse.model_validate(result.model_dump())
