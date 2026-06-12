"""Ingest, delete, search, and collection introspection."""

from __future__ import annotations

from docpipe.config.settings import DocpipeSettings
from docpipe.core.errors import ConfigurationError
from docpipe.core.types import IngestionConfig
from docpipe.ingestion.pipeline import IngestionPipeline
from docpipe.observability.metrics import record_ingest
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


class IngestService:
    def __init__(self, settings: DocpipeSettings, registry: PluginRegistry) -> None:
        self._settings = settings
        self._registry = registry

    async def ingest(self, req: IngestRequest) -> IngestResponse:
        resolved = resolve_fields(
            {"parser": req.parser, "tier": req.tier, "chunker": req.chunker},
            preset=req.preset,
            applicable={"parser", "tier", "chunker"},
            explicit=req.model_fields_set,
            endpoint="ingest",
        )
        parser_name = resolve_parser_name(resolved, req.source)
        parser = self._registry.get_parser(parser_name)
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
            **vector_fields_from_request(req, self._settings),
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
