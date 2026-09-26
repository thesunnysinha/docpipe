"""Evaluation endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from docpipe.schemas import EvaluateRequest, EvaluateResponse
from docpipe.server.deps import Auth, EvaluateServiceDep
from docpipe.server.router_errors import handle_docpipe_errors

router = APIRouter(tags=["evaluate"])


@router.post("/evaluate/run", response_model=EvaluateResponse)
@handle_docpipe_errors
async def evaluate_run(
    req: EvaluateRequest,
    _: Auth,
    service: EvaluateServiceDep,
) -> EvaluateResponse:
    """Run the requested evaluation over validated questions and metrics.

    Authentication is required. The evaluation service may connect to the
    configured vector store and model providers; evaluation results are returned
    in the response rather than persisted by this route.
    """
    return await service.run(req)
