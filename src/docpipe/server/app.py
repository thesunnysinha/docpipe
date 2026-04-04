"""FastAPI server for docpipe."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --- Request/Response models ---


class ParseRequest(BaseModel):
    source: str
    parser: str = "docling"
    output_format: str = "markdown"


class ParseResponse(BaseModel):
    source: str
    format: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractRequest(BaseModel):
    text: str
    description: str
    model_id: str
    extractor: str = "langextract"
    examples: list[dict[str, Any]] = Field(default_factory=list)
    entity_classes: list[str] = Field(default_factory=list)


class ExtractResponse(BaseModel):
    extractions: list[dict[str, Any]]


class RunRequest(BaseModel):
    source: str
    description: str
    model_id: str
    parser: str = "docling"
    extractor: str = "langextract"
    examples: list[dict[str, Any]] = Field(default_factory=list)
    entity_classes: list[str] = Field(default_factory=list)


class IngestRequest(BaseModel):
    source: str
    connection_string: str
    table_name: str
    embedding_provider: str
    embedding_model: str
    parser: str = "docling"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    ingest_mode: str = "both"


class IngestResponse(BaseModel):
    source: str
    chunks_ingested: int
    table_name: str
    table_created: bool


class SearchRequest(BaseModel):
    query: str
    connection_string: str
    table_name: str
    embedding_provider: str
    embedding_model: str
    top_k: int = 10


class SearchResponse(BaseModel):
    results: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    version: str
    plugins: dict[str, list[str]]


# --- App factory ---


def create_app() -> Any:
    """Create the FastAPI application."""
    from fastapi import FastAPI, HTTPException

    from docpipe._version import __version__
    from docpipe.core.errors import DocpipeError
    from docpipe.core.types import ExtractionSchema, IngestionConfig
    from docpipe.registry.registry import PluginRegistry

    app = FastAPI(
        title="docpipe",
        description="Unified document parsing, extraction, and ingestion API",
        version=__version__,
    )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        registry = PluginRegistry.get()
        return HealthResponse(
            status="ok",
            version=__version__,
            plugins={
                "parsers": registry.list_parsers(),
                "extractors": registry.list_extractors(),
            },
        )

    @app.post("/parse", response_model=ParseResponse)
    async def parse_document(req: ParseRequest) -> ParseResponse:
        try:
            registry = PluginRegistry.get()
            parser = registry.get_parser(req.parser)
            result = await parser.aparse(req.source)

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
        except DocpipeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/extract", response_model=ExtractResponse)
    async def extract_data(req: ExtractRequest) -> ExtractResponse:
        try:
            registry = PluginRegistry.get()
            extractor = registry.get_extractor(req.extractor)
            schema = ExtractionSchema(
                description=req.description,
                model_id=req.model_id,
                examples=req.examples,
                entity_classes=req.entity_classes,
            )
            results = await extractor.aextract(req.text, schema)
            return ExtractResponse(
                extractions=[r.model_dump() for r in results]
            )
        except DocpipeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/run")
    async def run_pipeline(req: RunRequest) -> dict[str, Any]:
        try:
            from docpipe.core.pipeline import Pipeline

            schema = ExtractionSchema(
                description=req.description,
                model_id=req.model_id,
                examples=req.examples,
                entity_classes=req.entity_classes,
            )
            pipeline = Pipeline(parser=req.parser, extractor=req.extractor)
            result = await pipeline.arun(req.source, schema)
            return result.model_dump()
        except DocpipeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/ingest", response_model=IngestResponse)
    async def ingest_document(req: IngestRequest) -> IngestResponse:
        try:
            from docpipe.ingestion.pipeline import IngestionPipeline

            registry = PluginRegistry.get()
            parser = registry.get_parser(req.parser)
            parsed = await parser.aparse(req.source)

            config = IngestionConfig(
                connection_string=req.connection_string,
                table_name=req.table_name,
                embedding_provider=req.embedding_provider,
                embedding_model=req.embedding_model,
                chunk_size=req.chunk_size,
                chunk_overlap=req.chunk_overlap,
                ingest_mode=req.ingest_mode,
            )
            ingestion = IngestionPipeline(config)
            result = await ingestion.aingest(parsed)
            return IngestResponse(
                source=result.source,
                chunks_ingested=result.chunks_ingested,
                table_name=result.table_name,
                table_created=result.table_created,
            )
        except DocpipeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/search", response_model=SearchResponse)
    async def search_documents(req: SearchRequest) -> SearchResponse:
        try:
            from docpipe.ingestion.pipeline import IngestionPipeline

            config = IngestionConfig(
                connection_string=req.connection_string,
                table_name=req.table_name,
                embedding_provider=req.embedding_provider,
                embedding_model=req.embedding_model,
            )
            ingestion = IngestionPipeline(config)
            results = ingestion.search(req.query, top_k=req.top_k)
            return SearchResponse(results=results)
        except DocpipeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.get("/plugins")
    async def list_plugins() -> dict[str, Any]:
        registry = PluginRegistry.get()
        return {
            "parsers": {
                name: registry.parser_info(name) for name in registry.list_parsers()
            },
            "extractors": {
                name: registry.extractor_info(name) for name in registry.list_extractors()
            },
        }

    return app


app = create_app()
