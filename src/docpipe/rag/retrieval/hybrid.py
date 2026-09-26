"""Native dense-and-sparse hybrid retrieval."""

from dataclasses import dataclass

from docpipe.rag.retrieval.base import RetrievalResult, VectorSearch


@dataclass(frozen=True, slots=True)
class HybridStrategy:
    """Use a vector plugin's negotiated native hybrid-search capability."""

    search: VectorSearch
    name: str = "hybrid"

    async def retrieve(self, question: str) -> RetrievalResult:
        return RetrievalResult(await self.search.hybrid(question))
