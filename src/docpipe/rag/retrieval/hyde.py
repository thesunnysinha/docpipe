"""Hypothetical-document embedding retrieval."""

from dataclasses import dataclass

from docpipe.rag.retrieval.base import RetrievalResult, TextRewriter, VectorSearch


@dataclass(frozen=True, slots=True)
class HydeStrategy:
    """Generate a hypothetical answer passage before vector search."""

    search: VectorSearch
    rewriter: TextRewriter
    prompt: str
    name: str = "hyde"

    async def retrieve(self, question: str) -> RetrievalResult:
        hypothetical = await self.rewriter.complete(self.prompt.format(question=question))
        chunks = await self.search.dense(hypothetical)
        return RetrievalResult(chunks, {"hypothetical_doc": hypothetical})
