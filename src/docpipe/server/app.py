"""FastAPI server for docpipe."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import psycopg2
from pydantic import BaseModel, Field, field_validator

from docpipe.core.types import DeleteRequest, DeleteResponse, RAGConfig, validate_table_name
from docpipe.rag.pipeline import RAGPipeline

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

    _validate_table_name = field_validator("table_name")(validate_table_name)


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
    filters: dict[str, Any] = Field(default_factory=dict)

    _validate_table_name = field_validator("table_name")(validate_table_name)


class SearchResponse(BaseModel):
    results: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    version: str
    plugins: dict[str, list[str]]


class RAGQueryRequest(BaseModel):
    question: str
    connection_string: str
    table_name: str
    embedding_provider: str
    embedding_model: str
    llm_provider: str
    llm_model: str
    api_key: str | None = None
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
    from fastapi.responses import StreamingResponse

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

    @app.delete("/ingest", response_model=DeleteResponse)
    async def delete_document(req: DeleteRequest) -> DeleteResponse:
        try:
            with psycopg2.connect(req.connection_string) as conn, conn.cursor() as cur:
                sql = (
                    f"DELETE FROM {req.table_name} "  # noqa: S608
                    "WHERE cmetadata->>'source' = %s"
                )
                cur.execute(sql, [req.source])
                deleted = cur.rowcount
            return DeleteResponse(
                table_name=req.table_name,
                source=req.source,
                chunks_deleted=deleted,
            )
        except psycopg2.errors.UndefinedTable as exc:
            raise HTTPException(
                status_code=404, detail=f"Table '{req.table_name}' not found"
            ) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

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
            results = ingestion.search(req.query, top_k=req.top_k, filters=req.filters)
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

    @app.post("/rag/query", response_model=RAGQueryResponse)
    async def rag_query(req: RAGQueryRequest) -> RAGQueryResponse:
        try:
            config = RAGConfig(
                connection_string=req.connection_string,
                table_name=req.table_name,
                embedding_provider=req.embedding_provider,
                embedding_model=req.embedding_model,
                llm_provider=req.llm_provider,
                llm_model=req.llm_model,
                llm_api_key=req.api_key,
                strategy=req.strategy,
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
            )
            pipeline = RAGPipeline(config)
            result = await pipeline.aquery(req.question)
            return RAGQueryResponse(
                query=result.query,
                answer=result.answer,
                strategy=result.strategy,
                chunks=[RAGChunkResponse(**c.model_dump()) for c in result.chunks],
                sources=result.sources,
                timing_seconds=result.timing_seconds,
            )
        except DocpipeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/rag/stream", response_class=StreamingResponse)
    async def rag_stream(req: RAGQueryRequest) -> StreamingResponse:
        try:
            config = RAGConfig(
                connection_string=req.connection_string,
                table_name=req.table_name,
                embedding_provider=req.embedding_provider,
                embedding_model=req.embedding_model,
                llm_provider=req.llm_provider,
                llm_model=req.llm_model,
                llm_api_key=req.api_key,
                strategy=req.strategy,
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
                stream=True,
            )
            pipeline = RAGPipeline(config)
        except DocpipeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        # NOTE: stream_query() is synchronous and blocks the event loop.
        # Acceptable for single-worker deployments; for async scale, wrap with asyncio.to_thread.
        def generate():
            try:
                for token in pipeline.stream_query(req.question):
                    yield f"data: {token}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as exc:  # noqa: BLE001
                logger.exception("stream_query failed")
                yield f"event: error\ndata: {exc}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    @app.post("/evaluate/run", response_model=EvaluateResponse)
    async def evaluate_run(req: EvaluateRequest) -> EvaluateResponse:
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
                rag_config=rag_config, questions=questions, metrics=req.metrics  # type: ignore[arg-type]
            )
            runner = EvalPipeline(cfg)
            result = await runner.arun()
            return EvaluateResponse(
                metrics=result.metrics.model_dump(exclude_none=True),
                num_questions=result.num_questions,
                timing_seconds=result.timing_seconds,
            )
        except DocpipeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/generate", response_model=GenerateResponse)
    async def generate(req: GenerateRequest) -> GenerateResponse:
        from docpipe.core.errors import ConfigurationError
        from docpipe.rag.pipeline import create_llm
        from langchain_core.messages import HumanMessage

        try:
            llm = create_llm(req.llm_provider, req.llm_model, req.api_key)
        except ConfigurationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        try:
            response = await asyncio.to_thread(llm.invoke, [HumanMessage(content=req.prompt)])
            content = response.content if hasattr(response, "content") else str(response)
            return GenerateResponse(content=content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    return app


app = create_app()
