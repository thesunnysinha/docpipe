"""RAG query and streaming."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from docpipe.bootstrap.runtime import DocpipeRuntime
from docpipe.config.settings import DocpipeSettings
from docpipe.core.types import TokenUsage
from docpipe.observability.metrics import observe_rag
from docpipe.rag.pipeline import RAGPipeline
from docpipe.schemas import RAGQueryRequest, RAGQueryResponse
from docpipe.server.plugin_requests import resolve_fields
from docpipe.server.request_mapping import rag_config_from_request
from docpipe.server.responses import rag_result_to_response

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, settings: DocpipeSettings, runtime: DocpipeRuntime | None = None) -> None:
        self._settings = settings
        self._runtime = runtime

    def _resolve_request(self, req: RAGQueryRequest, *, endpoint: str) -> RAGQueryRequest:
        resolved = resolve_fields(
            {"strategy": req.strategy, "reranker": req.reranker},
            preset=req.preset,
            applicable={"strategy", "reranker"},
            explicit=req.model_fields_set,
            endpoint=endpoint,
        )
        return req.model_copy(update=resolved)

    async def query(self, req: RAGQueryRequest) -> RAGQueryResponse:
        req = self._resolve_request(req, endpoint="rag/query")
        strategy = str(req.strategy or self._settings.default_rag_strategy)
        with observe_rag(strategy):
            config = rag_config_from_request(req, self._settings)
            pipeline = RAGPipeline(config, runtime=self._runtime)
            result = await pipeline.aquery(req.question)
            return rag_result_to_response(result)

    def stream(self, req: RAGQueryRequest) -> tuple[str, AsyncIterator[str]]:
        req = self._resolve_request(req, endpoint="rag/stream")
        strategy = str(req.strategy or self._settings.default_rag_strategy)
        config = rag_config_from_request(req, self._settings)
        config = config.model_copy(update={"stream": True})
        pipeline = RAGPipeline(config, runtime=self._runtime)

        async def generate() -> AsyncIterator[str]:
            try:
                with observe_rag(strategy):
                    async for token in pipeline.astream_query(req.question):
                        yield f"data: {token}\n\n"
                usage = pipeline.last_usage
                if isinstance(usage, TokenUsage):
                    meta = {"type": "usage", "usage": usage.model_dump(exclude_none=True)}
                    yield f"event: metadata\ndata: {json.dumps(meta)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "rag.stream.failed",
                    extra={"event": "rag.stream.failed", "error_type": type(exc).__name__},
                )
                yield "event: error\ndata: RAG streaming failed\n\n"

        return strategy, generate()
