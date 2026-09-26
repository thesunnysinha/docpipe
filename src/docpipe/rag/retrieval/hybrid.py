"""Native dense-and-sparse hybrid retrieval."""

from dataclasses import dataclass

from docpipe.rag.retrieval.base import RetrievalResult, VectorSearch


@dataclass(frozen=True, slots=True)
class HybridStrategy:
    """Use a vector plugin's negotiated native hybrid-search capability."""

    search: VectorSearch
    name: str = "hybrid"

    async def retrieve(self, question: str) -> RetrievalResult:
        """Run native hybrid search using the vector plugin's negotiated facets.

        No client-side sparse/dense score fusion is attempted: missing hybrid
        or required metadata-filter capability is reported by ``VectorSearch``
        as ``PluginCapabilityError``. Embedding and reader failures propagate.
        """
        return RetrievalResult(await self.search.hybrid(question))
