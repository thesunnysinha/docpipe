"""docpipe - Unified document parsing, structured extraction, and vector ingestion pipeline."""

from docpipe._version import __version__
from docpipe.core.errors import (
    ConfigurationError,
    DocpipeError,
    EvalError,
    ExtractionError,
    ExtractorNotFoundError,
    ExtractorNotInstalledError,
    IngestionError,
    ParseError,
    ParserNotFoundError,
    ParserNotInstalledError,
    RAGError,
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


def _register_builtins() -> None:
    """Register built-in parsers and extractors if their dependencies are available."""
    registry = PluginRegistry.get()

    try:
        from docpipe.parsers.docling_parser import DoclingParser

        registry.register_parser("docling", DoclingParser)
    except ImportError:
        pass

    try:
        from docpipe.extractors.langextract_extractor import LangExtractExtractor

        registry.register_extractor("langextract", LangExtractExtractor)
    except ImportError:
        pass

    try:
        from docpipe.extractors.langchain_extractor import LangChainExtractor

        registry.register_extractor("langchain", LangChainExtractor)
    except ImportError:
        pass


_register_builtins()


# --- Convenience functions ---


def parse(source: str, *, parser: str = "docling", **kwargs: object) -> ParsedDocument:
    """Parse a document using the specified parser."""
    p = PluginRegistry.get().get_parser(parser, **kwargs)
    return p.parse(source)


def extract(
    text: str,
    schema: ExtractionSchema,
    *,
    extractor: str = "langextract",
    **kwargs: object,
) -> list[ExtractionResult]:
    """Extract structured data using the specified extractor."""
    e = PluginRegistry.get().get_extractor(extractor, **kwargs)
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
    from docpipe.ingestion.pipeline import IngestionPipeline

    p = PluginRegistry.get().get_parser(parser)
    parsed = p.parse(source)
    ingestion = IngestionPipeline(config)
    return ingestion.ingest(parsed)


def rag(question: str, *, config: RAGConfig) -> RAGResult:
    """Answer a question using RAG against the user's vector store."""
    pipeline = RAGPipeline(config)
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
    "ConfigurationError",
    "DocpipeError",
    "ExtractionError",
    "ExtractorNotFoundError",
    "ExtractorNotInstalledError",
    "IngestionError",
    "ParseError",
    "ParserNotFoundError",
    "ParserNotInstalledError",
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
    "EvalError",
    "RAGError",
    # Convenience functions
    "extract",
    "ingest",
    "parse",
    "rag",
    "run",
]
