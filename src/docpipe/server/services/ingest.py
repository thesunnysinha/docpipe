"""Ingest, delete, search, and collection introspection."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from docpipe.config.settings import DocpipeSettings
from docpipe.core.errors import ConfigurationError
from docpipe.core.types import IngestionConfig, ParsedDocument
from docpipe.ingestion.pipeline import IngestionPipeline
from docpipe.observability.metrics import record_ingest
from docpipe.rag.lightrag_sync import sync_parsed_document
from docpipe.registry.registry import PluginRegistry
from docpipe.schemas import (
    IngestRequest,
    IngestResponse,
    ListSourcesRequest,
    ListSourcesResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SourceSummary,
)
from docpipe.schemas.delete import DeleteRequest, DeleteResponse
from docpipe.server.plugin_requests import resolve_fields, resolve_parser_name
from docpipe.server.request_mapping import vector_fields_from_request
from docpipe.vectorstores.base import resolve_vector_backend
from docpipe.vectorstores.factory import delete_by_source, list_collection_sources

logger = logging.getLogger(__name__)


class IngestService:
    def __init__(self, settings: DocpipeSettings, registry: PluginRegistry) -> None:
        self._settings = settings
        self._registry = registry

    async def _resolve_and_parse(
        self,
        req: IngestRequest,
    ) -> tuple[dict[str, Any], str, ParsedDocument]:
        resolved = resolve_fields(
            {"parser": req.parser, "tier": req.tier, "chunker": req.chunker},
            preset=req.preset,
            applicable={"parser", "tier", "chunker"},
            explicit=req.model_fields_set,
            endpoint="ingest",
        )
        parser_name = resolve_parser_name(resolved, req.source)
        parser = self._registry.get_parser(parser_name)

        from docpipe.server.parser_cache import get_cached_parse, store_cached_parse

        ttl = self._settings.parser_cache_ttl_seconds
        parsed = get_cached_parse(req.source, parser_name, ttl_seconds=ttl)
        if parsed is None:
            parsed = await parser.aparse(req.source)
            store_cached_parse(req.source, parser_name, parsed, ttl_seconds=ttl)
        return resolved, parser_name, parsed

    def _build_config(self, req: IngestRequest, resolved: dict[str, Any]) -> IngestionConfig:
        return IngestionConfig(
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
            **vector_fields_from_request(req, self._settings),
        )

    async def _finalize_ingest(
        self,
        req: IngestRequest,
        resolved: dict[str, Any],
        parsed: ParsedDocument,
        *,
        parser_name: str,
    ) -> IngestResponse:
        config = self._build_config(req, resolved)
        ingestion = IngestionPipeline(config)
        result = await ingestion.aingest(parsed)
        record_ingest(req.table_name, result.chunks_ingested)

        lightrag_synced = False
        if req.graph_index:
            if not req.lightrag_working_dir:
                raise ConfigurationError("lightrag_working_dir is required when graph_index=true")
            sync_parsed_document(working_dir=req.lightrag_working_dir, parsed=parsed)
            lightrag_synced = True

        response = IngestResponse(
            source=result.source,
            chunks_ingested=result.chunks_ingested,
            skipped=result.skipped,
            table_name=result.table_name,
            table_created=result.table_created,
            lightrag_synced=lightrag_synced,
        )
        try:
            from docpipe.db.repository import store_ingest_job

            store_ingest_job(
                source=result.source,
                table_name=result.table_name,
                preset=req.preset,
                parser=str(resolved.get("parser") or parser_name),
                chunks_ingested=result.chunks_ingested,
                skipped=result.skipped,
            )
        except Exception:  # noqa: BLE001
            logger.debug("ingest job persistence skipped", exc_info=True)
        return response

    @staticmethod
    def _progress_event(stage: str, *, percent: int, **extra: Any) -> str:
        payload = {"stage": stage, "percent": percent, **extra}
        return f"event: progress\ndata: {json.dumps(payload)}\n\n"

    async def ingest(self, req: IngestRequest) -> IngestResponse:
        resolved, parser_name, parsed = await self._resolve_and_parse(req)
        return await self._finalize_ingest(req, resolved, parsed, parser_name=parser_name)

    async def stream(self, req: IngestRequest) -> AsyncIterator[str]:
        """SSE progress stream for long-running ingest jobs."""
        try:
            yield self._progress_event("resolve", percent=5, message="Resolving preset and parser")
            resolved, parser_name, parsed = await self._resolve_and_parse(req)
            yield self._progress_event(
                "parse",
                percent=35,
                message="Document parsed",
                parser=parser_name,
            )
            yield self._progress_event("chunk", percent=55, message="Chunking and embedding")
            response = await self._finalize_ingest(
                req,
                resolved,
                parsed,
                parser_name=parser_name,
            )
            yield self._progress_event(
                "complete",
                percent=100,
                message="Ingest complete",
                result=response.model_dump(),
            )
            yield "data: [DONE]\n\n"
        except Exception as exc:  # noqa: BLE001
            logger.exception("ingest stream failed")
            yield f"event: error\ndata: {exc}\n\n"

    def delete(self, req: DeleteRequest) -> DeleteResponse:
        backend = resolve_vector_backend(
            config=req.vector_backend,
            default=self._settings.vector_backend,
        )
        source_label = (
            req.source_contains or "" if req.match_mode == "contains" else (req.source or "")
        )
        if backend == "turbovec":
            if not req.embedding_provider or not req.embedding_model:
                raise ConfigurationError(
                    "embedding_provider and embedding_model are required "
                    "when vector_backend=turbovec"
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

    def list_sources(self, req: ListSourcesRequest) -> ListSourcesResponse:
        backend = resolve_vector_backend(
            config=req.vector_backend,
            default=self._settings.vector_backend,
        )
        rows, total_chunks = list_collection_sources(
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

    def search(self, req: SearchRequest) -> SearchResponse:
        config = IngestionConfig(
            connection_string=req.connection_string,
            table_name=req.table_name,
            embedding_provider=req.embedding_provider,
            embedding_model=req.embedding_model,
            embedding_api_key=req.api_key,
            **vector_fields_from_request(req, self._settings),
        )
        ingestion = IngestionPipeline(config)
        results = ingestion.search(req.query, top_k=req.top_k, filters=req.filters)
        return SearchResponse(results=[SearchResultItem(**row) for row in results])
