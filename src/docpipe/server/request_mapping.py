"""Map API request schemas to core pipeline config objects."""

from __future__ import annotations

from typing import Any

from docpipe.config.settings import DocpipeSettings
from docpipe.core.types import RAGConfig
from docpipe.schemas.ingest import IngestRequest
from docpipe.schemas.rag import RAGQueryRequest
from docpipe.schemas.search import SearchRequest

VectorRequest = IngestRequest | SearchRequest | RAGQueryRequest


def vector_fields_from_request(
    req: VectorRequest,
    settings: DocpipeSettings,
) -> dict[str, Any]:
    backend = req.vector_backend or settings.vector_backend
    return {
        "vector_backend": backend,
        "turbovec_index_dir": req.turbovec_index_dir,
    }


def rag_config_from_request(
    req: RAGQueryRequest,
    settings: DocpipeSettings,
) -> RAGConfig:
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
        history=req.history,
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
