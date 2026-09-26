"""docpipe - Unified document parsing, structured extraction, and vector ingestion pipeline."""

from collections.abc import Iterator

from docpipe._version import __version__
from docpipe.agents.pipeline import AgentRAGPipeline
from docpipe.core.errors import (
    ChunkerNotFoundError,
    ConfigurationError,
    DocpipeError,
    EvalError,
    EvaluatorNotFoundError,
    ExtractionError,
    ExtractorNotFoundError,
    ExtractorNotInstalledError,
    IngestionError,
    ParseError,
    ParserNotFoundError,
    ParserNotInstalledError,
    RAGError,
    RerankerNotFoundError,
    UnsupportedFormatError,
)
from docpipe.core.extractor import BaseExtractor
from docpipe.core.parser import BaseParser
from docpipe.core.pipeline import Pipeline
from docpipe.core.types import (
    DocumentFormat,
    EvalConfig,
    EvalMetrics,
    EvalQuestion,
    EvalResult,
    ExtractionResult,
    ExtractionSchema,
    IngestionConfig,
    IngestionResult,
    PageContent,
    ParsedDocument,
    PipelineResult,
    RAGChunk,
    RAGConfig,
    RAGResult,
    SourceSpan,
)
from docpipe.eval.pipeline import EvalPipeline
from docpipe.rag.pipeline import RAGPipeline
from docpipe.registry.registry import PluginRegistry

# --- Convenience functions ---


def parse(source: str, *, parser: str = "docling", **kwargs: object) -> ParsedDocument:
    """Parse a document using the specified parser."""
    from docpipe.parsers.router import resolve_parser

    name = resolve_parser(parser, source=source, tier=str(kwargs.pop("tier", "balanced")))
    from docpipe.bootstrap.sdk import get_default_runtime

    p = get_default_runtime().legacy_registry.get_parser(name, **kwargs)
    return p.parse(source)


def extract(
    text: str,
    schema: ExtractionSchema,
    *,
    extractor: str = "langextract",
    **kwargs: object,
) -> list[ExtractionResult]:
    """Extract structured data using the specified extractor."""
    from docpipe.bootstrap.sdk import get_default_runtime

    e = get_default_runtime().legacy_registry.get_extractor(extractor, **kwargs)
    return e.extract(text, schema)


def run(
    source: str,
    schema: ExtractionSchema,
    *,
    parser: str = "docling",
    extractor: str = "langextract",
    ingestion_config: IngestionConfig | None = None,
) -> PipelineResult:
    """Run the full pipeline: parse + extract, optionally ingest."""
    pipeline = Pipeline(
        parser=parser,
        extractor=extractor,
        ingestion_config=ingestion_config,
    )
    return pipeline.run(source, schema)


def ingest(
    source: str,
    *,
    config: IngestionConfig,
    parser: str = "docling",
) -> IngestionResult:
    """Parse a document and ingest it into a vector store."""
    from docpipe.bootstrap.sdk import get_default_runtime
    from docpipe.ingestion.pipeline import IngestionPipeline

    p = get_default_runtime().legacy_registry.get_parser(parser)
    parsed = p.parse(source)
    ingestion = IngestionPipeline(config)
    return ingestion.ingest(parsed)


def query(question: str, *, config: RAGConfig) -> RAGResult:
    """Answer a question using RAG against the user's vector store."""
    pipeline = RAGPipeline(config)
    return pipeline.query(question)


def stream_query(question: str, *, config: RAGConfig) -> Iterator[str]:
    """Stream answer tokens for a RAG query against the user's vector store."""
    pipeline = RAGPipeline(config)
    return pipeline.stream_query(question)


def agent_query(question: str, *, config: RAGConfig, **kwargs: object) -> RAGResult:
    """Answer a question using AutoGen agents with vector-search tools."""
    from docpipe.agents.pipeline import AgentRAGPipeline

    pipeline = AgentRAGPipeline(config, **kwargs)  # type: ignore[arg-type]
    return pipeline.query(question)


__all__ = [
    "__version__",
    # Core types
    "DocumentFormat",
    "ExtractionResult",
    "ExtractionSchema",
    "IngestionConfig",
    "IngestionResult",
    "PageContent",
    "ParsedDocument",
    "PipelineResult",
    "SourceSpan",
    # Protocols
    "BaseExtractor",
    "BaseParser",
    # Pipeline
    "Pipeline",
    # Registry
    "PluginRegistry",
    # Errors
    "ChunkerNotFoundError",
    "ConfigurationError",
    "DocpipeError",
    "EvalError",
    "EvaluatorNotFoundError",
    "ExtractionError",
    "ExtractorNotFoundError",
    "ExtractorNotInstalledError",
    "IngestionError",
    "ParseError",
    "ParserNotFoundError",
    "ParserNotInstalledError",
    "RerankerNotFoundError",
    "UnsupportedFormatError",
    # RAG
    "RAGConfig",
    "RAGChunk",
    "RAGResult",
    "RAGPipeline",
    # Evaluation
    "EvalConfig",
    "EvalMetrics",
    "EvalQuestion",
    "EvalResult",
    "EvalPipeline",
    # Extra errors
    "RAGError",
    # Agents (optional autogen extra)
    "AgentRAGPipeline",
    # Convenience functions
    "agent_query",
    "extract",
    "ingest",
    "parse",
    "query",
    "run",
    "stream_query",
]
