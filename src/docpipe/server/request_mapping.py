"""Map API request schemas to core pipeline config objects."""

from __future__ import annotations

from typing import Any

from docpipe.config.compatibility import (
    resolve_vector_options,
    warn_legacy_field_once,
)
from docpipe.config.settings import DocpipeSettings
from docpipe.core.errors import ConfigurationError
from docpipe.core.types import RAGConfig
from docpipe.schemas.delete import DeleteRequest
from docpipe.schemas.ingest import IngestRequest
from docpipe.schemas.rag import RAGQueryRequest
from docpipe.schemas.search import SearchRequest
from docpipe.schemas.sources import ListSourcesRequest

VectorRequest = IngestRequest | SearchRequest | RAGQueryRequest | DeleteRequest | ListSourcesRequest


def vector_fields_from_request(
    req: VectorRequest,
    settings: DocpipeSettings,
) -> dict[str, Any]:
    """Resolve legacy and namespaced vector-store request fields.

    Explicit request values take precedence over configured defaults. Legacy
    aliases remain accepted during migration and emit a once-only warning;
    unsupported legacy backend names fail as configuration errors. The
    returned mapping is suitable for merging into vector-aware core configs.
    """
    if req.vector_backend is not None and req.vector_backend not in ("pgvector", "turbovec"):
        raise ConfigurationError(
            "vector_backend accepts only pgvector or turbovec; use vector_store.provider"
        )
    if "vector_backend" in req.model_fields_set and req.vector_store is None:
        warn_legacy_field_once("vector_backend")
    if "turbovec_index_dir" in req.model_fields_set and req.vector_store is None:
        warn_legacy_field_once("turbovec_index_dir")
    backend = req.vector_backend or settings.vector_backend
    namespaced_input = req.vector_store
    if namespaced_input is None and "vector_backend" not in req.model_fields_set:
        namespaced_input = settings.vector_store
    namespaced = resolve_vector_options(
        provider=backend,
        connection_string=req.connection_string,
        collection=req.table_name,
        index_root=req.turbovec_index_dir,
        bit_width=settings.turbovec_bit_width,
        namespaced=namespaced_input,
        explicit_legacy=req.model_fields_set,
    )
    return {
        "vector_backend": backend if namespaced.provider in ("pgvector", "turbovec") else None,
        "vector_store": namespaced,
        "turbovec_index_dir": req.turbovec_index_dir,
        "turbovec_bit_width": settings.turbovec_bit_width,
    }


def rag_config_from_request(
    req: RAGQueryRequest,
    settings: DocpipeSettings,
) -> RAGConfig:
    """Translate an API RAG request into the core pipeline configuration.

    Request credentials and options are mapped into runtime input fields while
    defaults for strategy, reranker, and vector-store provider come from the
    supplied settings. This function validates legacy vector options through
    :func:`vector_fields_from_request` but does not execute the RAG pipeline.
    """
    return RAGConfig(
        connection_string=req.connection_string,
        table_name=req.table_name,
        embedding_provider=req.embedding_provider,
        embedding_model=req.embedding_model,
        embedding_api_key=req.embedding_api_key or req.api_key,
        llm_provider=req.llm_provider,
        llm_model=req.llm_model,
        llm_api_key=req.api_key,
        strategy=req.strategy or settings.default_rag_strategy,  # type: ignore[arg-type]
        lightrag_working_dir=getattr(req, "lightrag_working_dir", None),
        top_k=req.top_k,
        max_chunks_per_source=req.max_chunks_per_source,
        system_prompt=req.system_prompt,
        history=[message.model_dump() for message in req.history],
        hyde_prompt=req.hyde_prompt,
        multi_query_prompt=req.multi_query_prompt,
        auto_strategy_prompt=req.auto_strategy_prompt,
        multi_query_count=req.multi_query_count,
        parent_window_size=req.parent_window_size,
        hybrid_bm25_weight=req.hybrid_bm25_weight,
        reranker=req.reranker or settings.default_reranker,  # type: ignore[arg-type]
        reranker_model=req.reranker_model,
        rerank_top_n=req.rerank_top_n,
        filters=req.filters,
        response_format=req.response_format,
        **vector_fields_from_request(req, settings),
    )
