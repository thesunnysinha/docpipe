"""Direct LLM generation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from docpipe.core.errors import ConfigurationError
from docpipe.observability.spans import trace_operation
from docpipe.schemas import GenerateRequest, GenerateResponse
from docpipe.server.deps import Auth, GenerateServiceDep
from docpipe.server.http_errors import docpipe_http_exception

router = APIRouter(tags=["generate"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    req: GenerateRequest,
    _: Auth,
    service: GenerateServiceDep,
) -> GenerateResponse:
    with trace_operation(
        "docpipe.generate",
        gen_ai_operation="chat",
        provider=req.llm_provider,
        model=req.llm_model,
    ):
        try:
            return await service.generate(req)
        except ConfigurationError as exc:
            raise docpipe_http_exception(exc) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
