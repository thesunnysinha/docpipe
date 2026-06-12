"""RAG query and streaming."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from docpipe.schemas import RAGQueryRequest, RAGQueryResponse
from docpipe.server.deps import Auth, RAGServiceDep
from docpipe.server.router_errors import handle_docpipe_errors

router = APIRouter(tags=["rag"])


@router.post("/rag/query", response_model=RAGQueryResponse)
@handle_docpipe_errors
async def rag_query(
    req: RAGQueryRequest,
    _: Auth,
    service: RAGServiceDep,
) -> RAGQueryResponse:
    return await service.query(req)


@router.post("/rag/stream", response_class=StreamingResponse)
@handle_docpipe_errors
async def rag_stream(
    req: RAGQueryRequest,
    _: Auth,
    service: RAGServiceDep,
) -> StreamingResponse:
    _, event_stream = service.stream(req)
    return StreamingResponse(event_stream, media_type="text/event-stream")
