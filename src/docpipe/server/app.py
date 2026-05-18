"""FastAPI server for docpipe."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Annotated, Any

import psycopg2
from fastapi import Depends, Request
from pydantic import BaseModel, Field, field_validator

from docpipe.core.types import (
    DeleteRequest,
    DeleteResponse,
    RAGConfig,
    TokenUsage,
    validate_table_name,
)
from docpipe.rag.pipeline import RAGPipeline
from docpipe.server.auth import require_auth

logger = logging.getLogger(__name__)

Auth = Annotated[None, Depends(require_auth)]


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
    # Optional per-request API key for the embedding provider.
    # When omitted, docpipe falls back to the provider's env var (e.g. GOOGLE_API_KEY).
    api_key: str | None = None
    parser: str = "docling"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    ingest_mode: str = "both"
    incremental: bool = False
    vector_backend: str | None = None
    turbovec_index_dir: str | None = None

    _validate_table_name = field_validator("table_name")(validate_table_name)


class IngestResponse(BaseModel):
    source: str
    chunks_ingested: int
    skipped: int = 0
    table_name: str
    table_created: bool


class SearchRequest(BaseModel):
    query: str
    connection_string: str
    table_name: str
    embedding_provider: str
    embedding_model: str
    api_key: str | None = None
    top_k: int = 10
    filters: dict[str, Any] = Field(default_factory=dict)
    vector_backend: str | None = None
    turbovec_index_dir: str | None = None

    _validate_table_name = field_validator("table_name")(validate_table_name)


class SearchResponse(BaseModel):
    results: list[dict[str, Any]]


class DependencyStatusResponse(BaseModel):
    name: str
    status: str
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    plugins: dict[str, list[str]]
    dependencies: list[DependencyStatusResponse] = Field(default_factory=list)


class RAGQueryRequest(BaseModel):
    question: str
    connection_string: str
    table_name: str
    embedding_provider: str
    embedding_model: str
    llm_provider: str
    llm_model: str
    # api_key applies to the LLM. embedding_api_key applies to the retrieval
    # embeddings; falls back to api_key when not provided (convenient when both
    # use the same provider and key, e.g. Google).
    api_key: str | None = None
    embedding_api_key: str | None = None
    strategy: str = "naive"
    top_k: int = 5
    system_prompt: str | None = None
    history: list[dict[str, str]] = Field(default_factory=list)
    hyde_prompt: str | None = None
    multi_query_count: int = 3
    parent_window_size: int = 3
    hybrid_bm25_weight: float = 0.5
    reranker: str = "none"
    reranker_model: str | None = None
    rerank_top_n: int | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    response_format: dict[str, Any] | None = None
    vector_backend: str | None = None
    turbovec_index_dir: str | None = None

    _validate_table_name = field_validator("table_name")(validate_table_name)


class RAGChunkResponse(BaseModel):
    content: str
    score: float
    source: str
    page: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    strategy: str
    chunks: list[RAGChunkResponse]
    sources: list[str]
    timing_seconds: float
    usage: TokenUsage | None = None


class EvaluateRequest(BaseModel):
    questions: list[dict[str, Any]]
    connection_string: str
    table_name: str
    embedding_provider: str
    embedding_model: str
    llm_provider: str
    llm_model: str
    strategy: str = "naive"
    metrics: list[str] = Field(default_factory=lambda: ["hit_rate", "answer_similarity"])

    _validate_table_name = field_validator("table_name")(validate_table_name)


class EvaluateResponse(BaseModel):
    metrics: dict[str, Any]
    num_questions: int
    timing_seconds: float


class GenerateRequest(BaseModel):
    prompt: str
    llm_provider: str
    llm_model: str
    api_key: str | None = None


class GenerateResponse(BaseModel):
    content: str


# --- App factory ---


def create_app() -> Any:
    """Create the FastAPI application."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, StreamingResponse

    from docpipe._version import __version__
    from docpipe.config import get_settings
    from docpipe.core.errors import DocpipeError
    from docpipe.core.types import ExtractionSchema, IngestionConfig
    from docpipe.observability import (
        configure_logging,
        configure_observability,
        shutdown_observability,
    )
    from docpipe.observability.metrics import (
        observe_rag,
        record_ingest,
        setup_prometheus_instrumentation,
    )
    from docpipe.observability.middleware import enrich_http_exception_span
    from docpipe.observability.spans import trace_operation
    from docpipe.observability.tracing import instrument_fastapi
    from docpipe.registry.registry import PluginRegistry
    from docpipe.server.health import build_health_response
    from docpipe.server.homepage import render_homepage
    from docpipe.server.http_errors import docpipe_http_exception, record_http_error_metrics

    settings = get_settings()
    configure_logging(settings)
    configure_observability()

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ARG001
        yield
        shutdown_observability()

    app = FastAPI(
        title="docpipe",
        description="Unified document parsing, extraction, and RAG ingestion API.",
        version=__version__,
        lifespan=lifespan,
    )
    setup_prometheus_instrumentation(app)
    instrument_fastapi(app)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> Any:
        enrich_http_exception_span(request, exc)
        detail = exc.detail
        if isinstance(detail, dict):
            route = request.scope.get("route")
            handler = getattr(route, "path", "unknown") if route else "unknown"
            record_http_error_metrics(
                str(detail.get("error_type", "docpipe")),
                str(detail.get("phase", "unknown")),
                handler,
            )
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=exc.status_code, content={"detail": detail})

    def _vector_fields_from_request(
        req: IngestRequest | SearchRequest | RAGQueryRequest,
    ) -> dict[str, Any]:
        backend = req.vector_backend or settings.vector_backend
        return {
            "vector_backend": backend,
            "turbovec_index_dir": req.turbovec_index_dir,
        }

    def _rag_config_from_request(req: RAGQueryRequest) -> RAGConfig:
        return RAGConfig(
            connection_string=req.connection_string,
            table_name=req.table_name,
            embedding_provider=req.embedding_provider,
            embedding_model=req.embedding_model,
            embedding_api_key=req.embedding_api_key or req.api_key,
            llm_provider=req.llm_provider,
            llm_model=req.llm_model,
            llm_api_key=req.api_key,
            strategy=req.strategy,  # type: ignore[arg-type]
            top_k=req.top_k,
            system_prompt=req.system_prompt,
            history=req.history,
            hyde_prompt=req.hyde_prompt,
            multi_query_count=req.multi_query_count,
            parent_window_size=req.parent_window_size,
            hybrid_bm25_weight=req.hybrid_bm25_weight,
            reranker=req.reranker,  # type: ignore[arg-type]
            reranker_model=req.reranker_model,
            rerank_top_n=req.rerank_top_n,
            filters=req.filters,
            response_format=req.response_format,
            **_vector_fields_from_request(req),
        )

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def homepage(_: Auth) -> HTMLResponse:
        registry = PluginRegistry.get()
        html = render_homepage(
            version=__version__,
            parsers=registry.list_parsers(),
            extractors=registry.list_extractors(),
        )
        return HTMLResponse(content=html)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Server health — no auth required (used by Docker healthcheck)."""
        registry = PluginRegistry.get()
        payload = build_health_response(
            __version__,
            {
                "parsers": registry.list_parsers(),
                "extractors": registry.list_extractors(),
            },
        )
        return HealthResponse(
            status=payload.status,
            version=payload.version,
            plugins=payload.plugins,
            dependencies=[
                DependencyStatusResponse(**dep.model_dump()) for dep in payload.dependencies
            ],
        )

    @app.post("/parse", response_model=ParseResponse)
    async def parse_document(req: ParseRequest, _: Auth) -> ParseResponse:
        with trace_operation("docpipe.parse"):
            return await _parse_document(req)

    async def _parse_document(req: ParseRequest) -> ParseResponse:
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
            raise docpipe_http_exception(e) from e

    @app.post("/extract", response_model=ExtractResponse)
    async def extract_data(req: ExtractRequest, _: Auth) -> ExtractResponse:
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
            return ExtractResponse(extractions=[r.model_dump() for r in results])
        except DocpipeError as e:
            raise docpipe_http_exception(e) from e

    @app.post("/run")
    async def run_pipeline(req: RunRequest, _: Auth) -> dict[str, Any]:
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
            raise docpipe_http_exception(e) from e

    @app.post("/ingest", response_model=IngestResponse)
    async def ingest_document(req: IngestRequest, _: Auth) -> IngestResponse:
        with trace_operation(
            "docpipe.ingest",
            docpipe_table_name=req.table_name,
            docpipe_incremental=req.incremental,
        ):
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
                    embedding_api_key=req.api_key,
                    chunk_size=req.chunk_size,
                    chunk_overlap=req.chunk_overlap,
                    ingest_mode=req.ingest_mode,  # type: ignore[arg-type]
                    incremental=req.incremental,
                    **_vector_fields_from_request(req),
                )
                ingestion = IngestionPipeline(config)
                result = await ingestion.aingest(parsed)
                record_ingest(req.table_name, result.chunks_ingested)
                return IngestResponse(
                    source=result.source,
                    chunks_ingested=result.chunks_ingested,
                    skipped=result.skipped,
                    table_name=result.table_name,
                    table_created=result.table_created,
                )
            except DocpipeError as e:
                raise docpipe_http_exception(e) from e

    @app.delete("/ingest", response_model=DeleteResponse)
    async def delete_document(req: DeleteRequest, _: Auth) -> DeleteResponse:
        with trace_operation("docpipe.ingest.delete", docpipe_table_name=req.table_name):
            try:
                from docpipe.ingestion.pipeline import IngestionPipeline
                from docpipe.vectorstores.base import resolve_vector_backend
                from docpipe.vectorstores.factory import delete_by_source

                backend = resolve_vector_backend(
                    config=req.vector_backend,
                    default=settings.vector_backend,
                )
                source_label = (
                    req.source_contains or ""
                    if req.match_mode == "contains"
                    else (req.source or "")
                )
                if backend == "turbovec":
                    if not req.embedding_provider or not req.embedding_model:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                "embedding_provider and embedding_model are required "
                                "when vector_backend=turbovec"
                            ),
                        )
                    emb_config = IngestionConfig(
                        connection_string=req.connection_string,
                        table_name=req.table_name,
                        embedding_provider=req.embedding_provider,
                        embedding_model=req.embedding_model,
                        embedding_api_key=req.embedding_api_key,
                        vector_backend=backend,
                        turbovec_index_dir=req.turbovec_index_dir,
                    )
                    embeddings = IngestionPipeline._create_embeddings(emb_config)
                    deleted = delete_by_source(
                        embeddings=embeddings,
                        table_name=req.table_name,
                        connection_string=req.connection_string,
                        vector_backend=backend,
                        turbovec_index_dir=req.turbovec_index_dir,
                        source=req.source,
                        source_contains=req.source_contains,
                        match_mode=req.match_mode,
                    )
                else:
                    deleted = delete_by_source(
                        embeddings=None,
                        table_name=req.table_name,
                        connection_string=req.connection_string,
                        vector_backend=backend,
                        source=req.source,
                        source_contains=req.source_contains,
                        match_mode=req.match_mode,
                    )
                return DeleteResponse(
                    table_name=req.table_name,
                    source=source_label,
                    chunks_deleted=deleted,
                )
            except HTTPException:
                raise
            except psycopg2.errors.UndefinedTable as exc:
                raise HTTPException(
                    status_code=404, detail=f"Table '{req.table_name}' not found"
                ) from exc
            except DocpipeError as e:
                raise docpipe_http_exception(e) from e
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/search", response_model=SearchResponse)
    async def search_documents(req: SearchRequest, _: Auth) -> SearchResponse:
        try:
            from docpipe.ingestion.pipeline import IngestionPipeline

            config = IngestionConfig(
                connection_string=req.connection_string,
                table_name=req.table_name,
                embedding_provider=req.embedding_provider,
                embedding_model=req.embedding_model,
                embedding_api_key=req.api_key,
                **_vector_fields_from_request(req),
            )
            ingestion = IngestionPipeline(config)
            results = ingestion.search(req.query, top_k=req.top_k, filters=req.filters)
            return SearchResponse(results=results)
        except DocpipeError as e:
            raise docpipe_http_exception(e) from e

    @app.get("/plugins")
    async def list_plugins(_: Auth) -> dict[str, Any]:
        registry = PluginRegistry.get()
        return {
            "parsers": {name: registry.parser_info(name) for name in registry.list_parsers()},
            "extractors": {
                name: registry.extractor_info(name) for name in registry.list_extractors()
            },
        }

    @app.post("/rag/query", response_model=RAGQueryResponse)
    async def rag_query(req: RAGQueryRequest, _: Auth) -> RAGQueryResponse:
        with observe_rag(req.strategy):
            try:
                config = _rag_config_from_request(req)
                pipeline = RAGPipeline(config)
                result = await pipeline.aquery(req.question)
                usage = result.usage if isinstance(result.usage, TokenUsage) else None
                return RAGQueryResponse(
                    query=result.query,
                    answer=result.answer,
                    strategy=result.strategy,
                    chunks=[RAGChunkResponse(**c.model_dump()) for c in result.chunks],
                    sources=result.sources,
                    timing_seconds=result.timing_seconds,
                    usage=usage,
                )
            except DocpipeError as e:
                raise docpipe_http_exception(e) from e

    @app.post("/rag/stream", response_class=StreamingResponse)
    async def rag_stream(req: RAGQueryRequest, _: Auth) -> StreamingResponse:
        try:
            config = _rag_config_from_request(req)
            config = config.model_copy(update={"stream": True})
            pipeline = RAGPipeline(config)
        except DocpipeError as e:
            raise docpipe_http_exception(e) from e

        # NOTE: stream_query() is synchronous and blocks the event loop.
        # Acceptable for single-worker deployments; for async scale, wrap with asyncio.to_thread.
        def generate():
            try:
                with observe_rag(req.strategy):
                    for token in pipeline.stream_query(req.question):
                        yield f"data: {token}\n\n"
                usage = pipeline.last_usage
                if isinstance(usage, TokenUsage):
                    meta = {"type": "usage", "usage": usage.model_dump(exclude_none=True)}
                    yield f"event: metadata\ndata: {json.dumps(meta)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as exc:  # noqa: BLE001
                logger.exception("stream_query failed")
                yield f"event: error\ndata: {exc}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    @app.post("/evaluate/run", response_model=EvaluateResponse)
    async def evaluate_run(req: EvaluateRequest, _: Auth) -> EvaluateResponse:
        try:
            from docpipe.core.types import EvalConfig, EvalQuestion, RAGConfig
            from docpipe.eval.pipeline import EvalPipeline

            rag_config = RAGConfig(
                connection_string=req.connection_string,
                table_name=req.table_name,
                embedding_provider=req.embedding_provider,
                embedding_model=req.embedding_model,
                llm_provider=req.llm_provider,
                llm_model=req.llm_model,
                strategy=req.strategy,
            )
            questions = [EvalQuestion(**q) for q in req.questions]
            cfg = EvalConfig(
                rag_config=rag_config,
                questions=questions,
                metrics=req.metrics,  # type: ignore[arg-type]
            )
            runner = EvalPipeline(cfg)
            result = await runner.arun()
            return EvaluateResponse(
                metrics=result.metrics.model_dump(exclude_none=True),
                num_questions=result.num_questions,
                timing_seconds=result.timing_seconds,
            )
        except DocpipeError as e:
            raise docpipe_http_exception(e) from e

    @app.post("/generate", response_model=GenerateResponse)
    async def generate(req: GenerateRequest, _: Auth) -> GenerateResponse:
        from langchain_core.messages import HumanMessage

        from docpipe.core.errors import ConfigurationError
        from docpipe.rag.pipeline import create_llm

        with trace_operation(
            "docpipe.generate",
            gen_ai_operation="chat",
            provider=req.llm_provider,
            model=req.llm_model,
        ):
            try:
                llm = create_llm(req.llm_provider, req.llm_model, req.api_key)
            except ConfigurationError as e:
                raise docpipe_http_exception(e) from e

            try:
                response = await asyncio.to_thread(llm.invoke, [HumanMessage(content=req.prompt)])
                return GenerateResponse(content=response.content)
            except Exception as e:
                logger.exception("LLM invocation failed")
                raise HTTPException(status_code=500, detail="LLM invocation failed") from e

    return app


app = create_app()
