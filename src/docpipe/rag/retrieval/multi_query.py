"""Multi-query retrieval with deterministic result fusion."""

from dataclasses import dataclass

from docpipe.core.types import RAGChunk
from docpipe.rag.retrieval.base import RetrievalResult, TextRewriter, VectorSearch


@dataclass(frozen=True, slots=True)
class MultiQueryStrategy:
    """Search the original question and generated query variants."""

    search: VectorSearch
    rewriter: TextRewriter
    prompt: str
    count: int = 3
    name: str = "multi_query"

    async def retrieve(self, question: str) -> RetrievalResult:
        """Search the original question plus up to ``count`` rewritten variants.

        The rewrite call runs first, then each query is searched sequentially.
        Duplicate source/content pairs retain their highest score and results
        are sorted descending. Metadata contains the accepted ``query_variants``;
        rewrite and vector-search failures propagate.
        """
        rendered = self.prompt.format(question=question, n=self.count)
        completion = await self.rewriter.complete(rendered)
        variants = tuple(
            line.strip()
            for line in completion.splitlines()
            if line.strip() and line.strip() != question
        )[: self.count]
        merged: dict[tuple[str, str], RAGChunk] = {}
        for query in (question, *variants):
            for chunk in await self.search.dense(query):
                key = (chunk.source, chunk.content)
                previous = merged.get(key)
                if previous is None or chunk.score > previous.score:
                    merged[key] = chunk
        chunks = tuple(sorted(merged.values(), key=lambda item: item.score, reverse=True))
        return RetrievalResult(chunks, {"query_variants": variants})
