"""Direct LLM generation."""

from __future__ import annotations

import asyncio
import logging

from langchain_core.messages import HumanMessage

from docpipe.core.errors import ConfigurationError
from docpipe.schemas import GenerateRequest, GenerateResponse

logger = logging.getLogger(__name__)


class GenerateService:
    """Invoke configured chat models for direct, non-streaming generation."""

    async def generate(self, req: GenerateRequest) -> GenerateResponse:
        """Send the prompt to the requested provider and return its response.

        An optional request API key is passed to the provider client. Provider
        configuration errors remain typed; other invocation failures are logged
        and raised as a generic runtime error for the route to map to HTTP 500.
        """
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
