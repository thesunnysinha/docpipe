"""Straightforward dense-vector retrieval."""

from dataclasses import dataclass

from docpipe.rag.retrieval.base import RetrievalResult, VectorSearch


@dataclass(frozen=True, slots=True)
class NaiveStrategy:
    """Retrieve the nearest dense-vector matches."""

    search: VectorSearch
    name: str = "naive"

    async def retrieve(self, question: str) -> RetrievalResult:
        """Return the nearest dense-vector matches for ``question``.

        Embedding, capability-negotiation, and vector-reader failures propagate
        unchanged from the underlying ``VectorSearch`` port.
        """
        return RetrievalResult(await self.search.dense(question))
