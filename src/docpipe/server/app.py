"""FastAPI server for docpipe."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from typing import Any, Literal

import psycopg2
from fastapi import Request

from docpipe.core.types import (
    DeleteRequest,
    DeleteResponse,
    RAGConfig,
    TokenUsage,
)
from docpipe.profiles.catalog import INSTALL_PROFILES
from docpipe.profiles.guardrails import build_plugins_payload
from docpipe.profiles.presets import list_runtime_presets
from docpipe.profiles.resolve import resolve_recommendation
from docpipe.rag.pipeline import RAGPipeline
from docpipe.schemas import (
    AgentQueryRequest,
    EvaluateRequest,
    EvaluateResponse,
    ExtractRequest,
    ExtractResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    ListSourcesRequest,
    ListSourcesResponse,
    ParseRequest,
    ParseResponse,
    PluginResolveRequest,
    PluginResolveResponse,
    ProfilesResponse,
    RAGChunkResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RunRequest,
    SearchRequest,
    SearchResponse,
    SourceSummary,
    TranscribeResponse,
)
from docpipe.server.deps import Auth
from docpipe.server.plugin_requests import resolve_fields, resolve_parser_name
from docpipe.server.request_mapping import rag_config_from_request, vector_fields_from_request

logger = logging.getLogger(__name__)


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
    from docpipe.observability.middleware import (
        RequestResponseLoggingMiddleware,
        enrich_http_exception_span,
    )
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
    if settings.http_request_logging_enabled:
        app.add_middleware(RequestResponseLoggingMiddleware)

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

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def homepage(_: Auth) -> HTMLResponse:
        registry = PluginRegistry.get()
        preset_catalog = list_runtime_presets()
        html = render_homepage(
            version=__version__,
            profile=settings.profile,
            presets=[{"name": name, **meta} for name, meta in preset_catalog.items()],
            parsers=registry.list_parsers(),
            extractors=registry.list_extractors(),
        )
        return HTMLResponse(content=html)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Server health — no auth required (used by Docker healthcheck)."""
        registry = PluginRegistry.get()
        return build_health_response(
            __version__,
            {
                "parsers": registry.list_parsers(),
                "extractors": registry.list_extractors(),
            },
        )

    @app.post("/parse", response_model=ParseResponse)
    async def parse_document(req: ParseRequest, _: Auth) -> ParseResponse:
        with trace_operation("docpipe.parse"):
            return await _parse_document(req)

    async def _parse_document(req: ParseRequest) -> ParseResponse:
        try:
            resolved = resolve_fields(
                {"parser": req.parser, "tier": req.tier},
                preset=req.preset,
                applicable={"parser", "tier"},
                explicit=req.model_fields_set,
                endpoint="parse",
            )
            registry = PluginRegistry.get()
            parser_name = resolve_parser_name(resolved, req.source)
            parser = registry.get_parser(parser_name)
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
            resolved = resolve_fields(
                {"extractor": req.extractor},
                preset=None,
                applicable={"extractor"},
                explicit=req.model_fields_set,
            )
            registry = PluginRegistry.get()
            extractor = registry.get_extractor(str(resolved["extractor"]))
            schema = ExtractionSchema(
                description=req.description,
                model_id=req.model_id,
                examples=req.examples,
                entity_classes=req.entity_classes,
                strict=getattr(req, "strict", True),
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
                strict=getattr(req, "strict", True),
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
            docpipe_profile=settings.profile,
            docpipe_preset=req.preset,
            docpipe_table_name=req.table_name,
            docpipe_incremental=req.incremental,
        ):
            try:
                from docpipe.ingestion.pipeline import IngestionPipeline

                resolved = resolve_fields(
                    {"parser": req.parser, "tier": req.tier, "chunker": req.chunker},
                    preset=req.preset,
                    applicable={"parser", "tier", "chunker"},
                    explicit=req.model_fields_set,
                    endpoint="ingest",
                )
                registry = PluginRegistry.get()
                parser_name = resolve_parser_name(resolved, req.source)
                parser = registry.get_parser(parser_name)
                parsed = await parser.aparse(req.source)

                config = IngestionConfig(
                    connection_string=req.connection_string,
                    table_name=req.table_name,
                    embedding_provider=req.embedding_provider,
                    embedding_model=req.embedding_model,
                    embedding_api_key=req.api_key,
                    chunker=str(resolved["chunker"]),
                    chunk_method=req.chunk_method,  # type: ignore[arg-type]
                    chunk_size=req.chunk_size,
                    chunk_overlap=req.chunk_overlap,
                    ingest_mode=req.ingest_mode,  # type: ignore[arg-type]
                    incremental=req.incremental,
                    chunk_metadata=req.chunk_metadata,
                    **vector_fields_from_request(req, settings),
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

    @app.post("/collection/sources", response_model=ListSourcesResponse)
    async def list_collection_sources(req: ListSourcesRequest, _: Auth) -> ListSourcesResponse:
        """Distinct ingested sources in a vector collection (debug / reconciliation)."""
        with trace_operation("docpipe.collection.sources", docpipe_table_name=req.table_name):
            try:
                from docpipe.core.errors import ConfigurationError
                from docpipe.vectorstores.base import resolve_vector_backend
                from docpipe.vectorstores.factory import list_collection_sources as list_sources

                backend = resolve_vector_backend(
                    config=req.vector_backend,
                    default=settings.vector_backend,
                )
                rows, total_chunks = list_sources(
                    table_name=req.table_name,
                    connection_string=req.connection_string,
                    vector_backend=backend,
                    filters=req.filters or None,
                )
                return ListSourcesResponse(
                    table_name=req.table_name,
                    sources=[SourceSummary(**row) for row in rows],
                    total_chunks=total_chunks,
                )
            except ConfigurationError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
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
                **vector_fields_from_request(req, settings),
            )
            ingestion = IngestionPipeline(config)
            results = ingestion.search(req.query, top_k=req.top_k, filters=req.filters)
            return SearchResponse(results=results)
        except DocpipeError as e:
            raise docpipe_http_exception(e) from e

    @app.get("/plugins")
    async def list_plugins(_: Auth) -> dict[str, Any]:
        return build_plugins_payload()

    @app.get("/profiles", response_model=ProfilesResponse)
    async def list_profiles(_: Auth) -> ProfilesResponse:
        return ProfilesResponse(
            install_profile=settings.profile,
            install_profiles=INSTALL_PROFILES,
            runtime_presets=list_runtime_presets(),
            server_defaults={
                "default_parser": settings.default_parser,
                "default_parser_tier": settings.default_parser_tier,
                "default_chunker": settings.default_chunker,
                "default_reranker": settings.default_reranker,
                "default_rag_strategy": settings.default_rag_strategy,
                "default_runtime_preset": settings.default_runtime_preset,
            },
        )

    @app.post("/plugins/resolve", response_model=PluginResolveResponse)
    async def plugins_resolve(req: PluginResolveRequest, _: Auth) -> PluginResolveResponse:
        try:
            data = resolve_recommendation(
                source=req.source,
                goal=req.goal,
                preset=req.preset,
            )
            return PluginResolveResponse(**data)
        except DocpipeError as exc:
            raise docpipe_http_exception(exc) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/agents/query", response_model=RAGQueryResponse)
    async def agents_query(req: AgentQueryRequest, _: Auth) -> RAGQueryResponse:
        rag_resolved = resolve_fields(
            {"strategy": req.strategy, "reranker": req.reranker},
            preset=req.preset,
            applicable={"strategy", "reranker"},
            explicit=req.model_fields_set,
            endpoint="agents/query",
        )
        agent_resolved = resolve_fields(
            {
                "agent_backend": req.agent_backend,
                "enable_parse_tool": req.enable_parse_tool,
            },
            preset=req.preset,
            applicable={"agent_backend", "enable_parse_tool"},
            explicit=req.model_fields_set,
            endpoint="agents/query",
        )
        req = req.model_copy(
            update={
                **rag_resolved,
                **{k: v for k, v in agent_resolved.items() if k in agent_resolved},
            }
        )
        strategy = str(req.strategy or settings.default_rag_strategy)
        with observe_rag(strategy):
            try:
                config = rag_config_from_request(req, settings)
                if req.agent_backend == "langgraph":
                    from docpipe.agents.langgraph_pipeline import LangGraphRAGPipeline

                    pipeline = LangGraphRAGPipeline(config, max_steps=req.max_steps)
                    result = await asyncio.to_thread(pipeline.query, req.question)
                else:
                    from docpipe.agents.pipeline import AgentRAGPipeline

                    pipeline = AgentRAGPipeline(
                        config,
                        enable_reviewer=req.enable_reviewer,
                        enable_parse_tool=req.enable_parse_tool,
                        parse_tool_parser=req.parse_tool_parser,
                        max_tool_iterations=req.max_tool_iterations,
                        max_turns=req.max_turns,
                    )
                    result = await asyncio.to_thread(pipeline.query, req.question)
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

    @app.post("/rag/query", response_model=RAGQueryResponse)
    async def rag_query(req: RAGQueryRequest, _: Auth) -> RAGQueryResponse:
        resolved = resolve_fields(
            {"strategy": req.strategy, "reranker": req.reranker},
            preset=req.preset,
            applicable={"strategy", "reranker"},
            explicit=req.model_fields_set,
            endpoint="rag/query",
        )
        req = req.model_copy(update=resolved)
        strategy = str(req.strategy or settings.default_rag_strategy)
        with observe_rag(strategy):
            try:
                config = rag_config_from_request(req, settings)
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
        resolved = resolve_fields(
            {"strategy": req.strategy, "reranker": req.reranker},
            preset=req.preset,
            applicable={"strategy", "reranker"},
            explicit=req.model_fields_set,
            endpoint="rag/stream",
        )
        req = req.model_copy(update=resolved)
        strategy = str(req.strategy or settings.default_rag_strategy)
        try:
            config = rag_config_from_request(req, settings)
            config = config.model_copy(update={"stream": True})
            pipeline = RAGPipeline(config)
        except DocpipeError as e:
            raise docpipe_http_exception(e) from e

        def generate():
            try:
                with observe_rag(strategy):
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
            from docpipe.core.types import EvalConfig, EvalQuestion
            from docpipe.eval.pipeline import EvalPipeline

            resolved = resolve_fields(
                {"strategy": req.strategy, "evaluator": req.evaluator},
                preset=req.preset,
                applicable={"strategy", "evaluator"},
                explicit=req.model_fields_set,
                endpoint="evaluate/run",
            )
            rag_config = RAGConfig(
                connection_string=req.connection_string,
                table_name=req.table_name,
                embedding_provider=req.embedding_provider,
                embedding_model=req.embedding_model,
                llm_provider=req.llm_provider,
                llm_model=req.llm_model,
                strategy=resolved["strategy"],  # type: ignore[arg-type]
            )
            questions = [EvalQuestion(**q) for q in req.questions]
            cfg = EvalConfig(
                rag_config=rag_config,
                questions=questions,
                evaluator=str(resolved["evaluator"]),
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

    @app.post("/transcribe", response_model=TranscribeResponse)
    async def transcribe(request: Request, _: Auth) -> TranscribeResponse:
        from docpipe.core.errors import DocpipeError
        from docpipe.speech.service import TranscriptionService

        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=400, detail="Multipart field 'file' is required.")

        backend_raw = form.get("backend")
        backend: Literal["openai", "vibevoice", "vibevoice_remote"] | None = None
        if backend_raw in ("openai", "vibevoice", "vibevoice_remote"):
            backend = backend_raw  # type: ignore[assignment]

        output_raw = form.get("output_format") or "plain"
        output_format: Literal["plain", "structured"] = (
            "structured" if output_raw == "structured" else "plain"
        )
        hotwords_raw = form.get("hotwords")
        api_key_raw = form.get("api_key")
        language_raw = form.get("language")

        filename = getattr(upload, "filename", None) or "audio.wav"
        suffix = os.path.splitext(filename)[1] or ".wav"
        hotword_list = [w.strip() for w in str(hotwords_raw or "").split(",") if w.strip()]
        temp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                temp_path = tmp.name
                while chunk := await upload.read(1024 * 1024):
                    tmp.write(chunk)
            resolved_backend = backend or settings.transcribe_default_backend
            with trace_operation("docpipe.transcribe", docpipe_backend=resolved_backend):
                result = await TranscriptionService.atranscribe_file(
                    temp_path,
                    settings=settings,
                    backend=backend,
                    api_key=str(api_key_raw) if api_key_raw else None,
                    hotwords=hotword_list or None,
                    language=str(language_raw) if language_raw else None,
                    output_format=output_format,
                )
            return TranscribeResponse(
                text=result.text,
                backend=result.backend,
                raw_text=result.raw_text,
                segments=[seg.model_dump() for seg in result.segments],
                metadata=result.metadata,
            )
        except DocpipeError as exc:
            raise docpipe_http_exception(exc) from exc
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    logger.warning("Failed to remove temp audio file", exc_info=True)

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
