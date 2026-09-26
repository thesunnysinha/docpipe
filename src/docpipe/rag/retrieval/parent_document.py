"""Parent-document expansion based on typed source filters."""

from dataclasses import dataclass

from docpipe.core.types import RAGChunk
from docpipe.plugins.contracts.vectorstore import Equals
from docpipe.rag.retrieval.base import RetrievalResult, VectorSearch


@dataclass(frozen=True, slots=True)
class ParentDocumentStrategy:
    """Expand initial matches with nearby content from each source."""

    search: VectorSearch
    window_size: int = 3
    name: str = "parent_document"

    async def retrieve(self, question: str) -> RetrievalResult:
        """Expand dense matches with more matching chunks from each source.

        Performs the initial search, then one filtered search per distinct seed
        source, sequentially, with ``window_size`` as each expansion limit.
        Duplicate source/content pairs keep the highest score. Filtering requires
        metadata-filter capability; dependency errors propagate.
        """
        seeds = await self.search.dense(question)
        merged: dict[tuple[str, str], RAGChunk] = {
            (chunk.source, chunk.content): chunk for chunk in seeds
        }
        for source in dict.fromkeys(chunk.source for chunk in seeds):
            expanded = await self.search.dense(
                question,
                filter=Equals("source", source),
                limit=self.window_size,
            )
            for chunk in expanded:
                key = (chunk.source, chunk.content)
                previous = merged.get(key)
                if previous is None or chunk.score > previous.score:
                    merged[key] = chunk
        chunks = tuple(sorted(merged.values(), key=lambda item: item.score, reverse=True))
        return RetrievalResult(chunks)
