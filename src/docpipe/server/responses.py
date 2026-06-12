"""Map core pipeline results to API response schemas."""

from __future__ import annotations

from docpipe.core.types import RAGResult, TokenUsage
from docpipe.schemas import RAGChunkResponse, RAGQueryResponse


def rag_result_to_response(result: RAGResult) -> RAGQueryResponse:
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
