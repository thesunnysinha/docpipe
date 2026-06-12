"""Direct LLM generation."""

from __future__ import annotations

import asyncio
import logging

from langchain_core.messages import HumanMessage

from docpipe.core.errors import ConfigurationError
from docpipe.schemas import GenerateRequest, GenerateResponse

logger = logging.getLogger(__name__)


class GenerateService:
    async def generate(self, req: GenerateRequest) -> GenerateResponse:
        from docpipe.rag.pipeline import create_llm

        try:
            llm = create_llm(req.llm_provider, req.llm_model, req.api_key)
        except ConfigurationError:
            raise

        try:
            response = await asyncio.to_thread(llm.invoke, [HumanMessage(content=req.prompt)])
            return GenerateResponse(content=response.content)
        except Exception as exc:
            logger.exception("LLM invocation failed")
            raise RuntimeError("LLM invocation failed") from exc
