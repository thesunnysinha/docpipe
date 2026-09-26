"""Agentic RAG endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from docpipe.schemas import AgentQueryRequest, RAGQueryResponse
from docpipe.server.deps import AgentServiceDep, Auth
from docpipe.server.router_errors import handle_docpipe_errors

router = APIRouter(tags=["agents"])


@router.post("/agents/query", response_model=RAGQueryResponse)
@handle_docpipe_errors
async def agents_query(
    req: AgentQueryRequest,
    _: Auth,
    service: AgentServiceDep,
) -> RAGQueryResponse:
    """Run an authenticated agentic RAG query from the validated request.

    The service selects the configured agent and retrieval strategy and may call
    the configured embedding, vector-store, and language-model providers. Known
    Docpipe and public integration errors are translated by the route decorator.
    """
    return await service.query(req)
