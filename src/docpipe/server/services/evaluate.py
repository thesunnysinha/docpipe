"""RAG evaluation runs."""

from __future__ import annotations

from docpipe.config.settings import DocpipeSettings
from docpipe.core.types import EvalConfig, RAGConfig
from docpipe.eval.pipeline import EvalPipeline
from docpipe.schemas import EvaluateRequest, EvaluateResponse
from docpipe.server.plugin_requests import resolve_fields


class EvaluateService:
    def __init__(self, settings: DocpipeSettings) -> None:
        self._settings = settings

    async def run(self, req: EvaluateRequest) -> EvaluateResponse:
        resolved = resolve_fields(
            {"strategy": req.strategy, "evaluator": req.evaluator},
            preset=req.preset,
            applicable={"strategy", "evaluator"},
            explicit=req.model_fields_set,
            endpoint="evaluate/run",
        )
        rag_config = RAGConfig(
            connection_string=req.connection_string,
            table_name=req.table_name,
            embedding_provider=req.embedding_provider,
            embedding_model=req.embedding_model,
            llm_provider=req.llm_provider,
            llm_model=req.llm_model,
            strategy=resolved["strategy"],  # type: ignore[arg-type]
        )
        cfg = EvalConfig(
            rag_config=rag_config,
            questions=req.questions,
            evaluator=str(resolved["evaluator"]),
            metrics=req.metrics,  # type: ignore[arg-type]
        )
        runner = EvalPipeline(cfg)
        result = await runner.arun()
        return EvaluateResponse(
            metrics=result.metrics.model_dump(exclude_none=True),
            num_questions=result.num_questions,
            timing_seconds=result.timing_seconds,
        )
