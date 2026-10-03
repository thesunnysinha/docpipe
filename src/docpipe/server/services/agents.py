"""Agentic RAG orchestration."""

from __future__ import annotations

import asyncio

from docpipe.config.settings import DocpipeSettings
from docpipe.observability.metrics import observe_rag
from docpipe.schemas import AgentQueryRequest, RAGQueryResponse
from docpipe.server.plugin_requests import resolve_fields
from docpipe.server.request_mapping import rag_config_from_request
from docpipe.server.responses import rag_result_to_response


class AgentService:
    """Resolve request presets and execute the selected agentic RAG pipeline."""

    def __init__(self, settings: DocpipeSettings) -> None:
        """Keep the application settings used to supply RAG defaults."""
        self._settings = settings

    async def query(self, req: AgentQueryRequest) -> RAGQueryResponse:
        """Run an agent query, offloading synchronous pipeline work to a thread.

        Request-explicit strategy and agent options take precedence over preset
        values; remaining defaults come from the injected settings. The selected
        pipeline can access configured embedding, vector-store, and LLM services.
        """
        rag_resolved = resolve_fields(
            {"strategy": req.strategy, "reranker": req.reranker},
            preset=req.preset,
            applicable={"strategy", "reranker"},
            explicit=req.model_fields_set,
            endpoint="agents/query",
        )
        agent_resolved = resolve_fields(
            {
                "agent_backend": req.agent_backend,
                "enable_parse_tool": req.enable_parse_tool,
            },
            preset=req.preset,
            applicable={"agent_backend", "enable_parse_tool"},
            explicit=req.model_fields_set,
            endpoint="agents/query",
        )
        req = req.model_copy(update={**rag_resolved, **agent_resolved})
        strategy = str(req.strategy or self._settings.default_rag_strategy)

        with observe_rag(strategy):
            config = rag_config_from_request(req, self._settings)
            if req.agent_backend == "runtime":
                from docpipe.agents.runtime_pipeline import RuntimeRAGPipeline

                runtime_pipeline = await asyncio.to_thread(
                    RuntimeRAGPipeline,
                    config,
                    enable_parse_tool=req.enable_parse_tool,
                    parse_tool_parser=req.parse_tool_parser,
                    max_steps=req.max_steps,
                )
                result = await runtime_pipeline.aquery(req.question, req.session_id)
            elif req.agent_backend == "langgraph":
                from docpipe.agents.langgraph_pipeline import LangGraphRAGPipeline

                pipeline = LangGraphRAGPipeline(config, max_steps=req.max_steps)
                result = await asyncio.to_thread(pipeline.query, req.question)
            else:
                from docpipe.agents.pipeline import AgentRAGPipeline

                pipeline = AgentRAGPipeline(
                    config,
                    enable_reviewer=req.enable_reviewer,
                    enable_parse_tool=req.enable_parse_tool,
                    parse_tool_parser=req.parse_tool_parser,
                    max_tool_iterations=req.max_tool_iterations,
                    max_turns=req.max_turns,
                )
                result = await asyncio.to_thread(pipeline.query, req.question)
            return rag_result_to_response(result)
