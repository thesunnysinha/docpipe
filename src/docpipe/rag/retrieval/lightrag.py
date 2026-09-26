"""Optional LightRAG retrieval behind a lazy, injected graph-query boundary."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.core.errors import ConfigurationError, RAGError
from docpipe.core.types import RAGChunk
from docpipe.rag.retrieval.base import RetrievalResult, VectorSearch

GraphQuery = Callable[[str, str], Awaitable[str]]


@dataclass(frozen=True, slots=True)
class LightRAGStrategy:
    """Query a separately managed graph index, falling back on empty results."""

    search: VectorSearch
    working_dir: str | None
    query_graph: GraphQuery
    name: str = "lightrag"

    async def retrieve(self, question: str) -> RetrievalResult:
        """Query the configured graph index, using dense search for empty output.

        A missing ``working_dir`` raises ``ConfigurationError``. A non-empty
        graph response becomes one synthetic source chunk; an empty response
        falls back to dense vector search. Graph/model errors are not converted
        to fallback results and propagate to the caller.
        """
        if not self.working_dir:
            raise ConfigurationError("lightrag_working_dir is required when strategy='lightrag'")
        answer = await self.query_graph(question, self.working_dir)
        chunks: tuple[RAGChunk, ...]
        if answer:
            chunks = (
                RAGChunk(
                    content=answer[:2000],
                    score=1.0,
                    source="lightrag",
                    metadata={"strategy": "lightrag"},
                ),
            )
        else:
            chunks = await self.search.dense(question)
        return RetrievalResult(chunks, {"lightrag_working_dir": self.working_dir})


def graph_query_adapter(runner: BoundedBlockingRunner) -> GraphQuery:
    """Build a lazy adapter for the separately managed LightRAG index.

    The optional package is imported only when the returned callable is used.
    Synchronous index construction and querying run through ``runner`` so they
    do not block the event loop; cancellation and execution errors follow the
    blocking runner's contract.
    """

    async def query(question: str, working_dir: str) -> str:
        """Query one graph index; raise a dependency error when not installed."""
        try:
            from lightrag import LightRAG, QueryParam
        except ImportError as error:
            raise RAGError(
                "lightrag strategy requires lightrag. Install docpipe-sdk[lightrag]"
            ) from error

        def invoke() -> str:
            """Construct a request-scoped LightRAG object and query it."""
            rag = LightRAG(working_dir=working_dir)
            return str(rag.query(question, param=QueryParam(mode="hybrid")) or "")

        return await runner.run(invoke)

    return query
