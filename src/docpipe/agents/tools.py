"""AutoGen tools that wrap docpipe retrieval and parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from docpipe.core.errors import ConfigurationError

if TYPE_CHECKING:
    from docpipe.rag.pipeline import RAGPipeline


def make_search_tool(rag_pipeline: RAGPipeline):
    """Build a vector-search tool bound to a RAGPipeline instance."""

    def search_documents(query: str) -> str:
        """Search ingested documents for passages relevant to a question or topic."""
        chunks = rag_pipeline._retrieve_naive(query)  # noqa: SLF001
        if not chunks:
            return "No relevant documents found."
        lines: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            source = chunk.source or "unknown"
            page = f", page {chunk.page}" if chunk.page is not None else ""
            lines.append(f"[{i}] ({source}{page})\n{chunk.content}")
        return "\n\n".join(lines)

    return search_documents


def make_parse_tool(*, parser: str = "markitdown"):
    """Build a document parse tool using a registered docpipe parser."""

    def parse_document(source: str) -> str:
        """Parse a document path or URL into markdown/text using docpipe."""
        from docpipe.registry.registry import PluginRegistry

        p = PluginRegistry.get().get_parser(parser)
        parsed = p.parse(source)
        return parsed.markdown or parsed.text

    return parse_document


def require_autogen() -> None:
    """Raise if AutoGen optional dependencies are missing."""
    try:
        import autogen_agentchat  # noqa: F401
        import autogen_core  # noqa: F401
    except ImportError as err:
        raise ConfigurationError(
            "AutoGen is not installed. Install with: pip install docpipe-sdk[autogen]"
        ) from err
