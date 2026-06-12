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


def _register_builtins() -> None:
    """Register built-in plugins if their dependencies are available."""
    registry = PluginRegistry.get()

    _try_register_parser(registry, "docling", "docpipe.parsers.docling_parser", "DoclingParser")
    _try_register_parser(
        registry, "markitdown", "docpipe.parsers.markitdown_parser", "MarkItDownParser"
    )
    _try_register_parser(registry, "glm-ocr", "docpipe.parsers.glm_ocr_parser", "GLMOCRParser")
    _try_register_parser(registry, "pymupdf", "docpipe.parsers.pymupdf_parser", "PyMuPDFParser")
    _try_register_parser(registry, "mineru", "docpipe.parsers.mineru_parser", "MinerUParser")
    _try_register_parser(
        registry, "paddleocr", "docpipe.parsers.paddleocr_parser", "PaddleOCRParser"
    )
    _try_register_parser(
        registry, "unstructured", "docpipe.parsers.unstructured_parser", "UnstructuredParser"
    )

    _try_register_extractor(
        registry, "langextract", "docpipe.extractors.langextract_extractor", "LangExtractExtractor"
    )
    _try_register_extractor(
        registry, "langchain", "docpipe.extractors.langchain_extractor", "LangChainExtractor"
    )
    _try_register_extractor(
        registry, "outlines", "docpipe.extractors.outlines_extractor", "OutlinesExtractor"
    )

    _try_register_chunker(
        registry, "recursive", "docpipe.chunkers.recursive_chunker", "RecursiveChunker"
    )
    _try_register_chunker(
        registry, "semchunk", "docpipe.chunkers.semchunk_chunker", "SemchunkChunker"
    )
    _try_register_chunker(
        registry, "chonkie-semantic", "docpipe.chunkers.chonkie_chunker", "ChonkieSemanticChunker"
    )
    _try_register_chunker(
        registry, "chonkie-late", "docpipe.chunkers.chonkie_chunker", "ChonkieLateChunker"
    )

    _try_register_reranker(
        registry, "flashrank", "docpipe.rerankers.flashrank_reranker", "FlashRankReranker"
    )
    _try_register_reranker(
        registry, "cohere", "docpipe.rerankers.cohere_reranker", "CohereReranker"
    )
    _try_register_reranker(registry, "bge", "docpipe.rerankers.bge_reranker", "BGEReranker")
    _try_register_reranker(registry, "mxbai", "docpipe.rerankers.mxbai_reranker", "MxbaiReranker")

    _try_register_evaluator(
        registry, "builtin", "docpipe.eval.builtin_evaluator", "BuiltinEvaluator"
    )
    _try_register_evaluator(registry, "ragas", "docpipe.eval.ragas_evaluator", "RagasEvaluator")


def _try_register_parser(registry: PluginRegistry, name: str, module: str, cls_name: str) -> None:
    try:
        mod = __import__(module, fromlist=[cls_name])
        registry.register_parser(name, getattr(mod, cls_name))
    except ImportError:
        pass


def _try_register_extractor(
    registry: PluginRegistry, name: str, module: str, cls_name: str
) -> None:
    try:
        mod = __import__(module, fromlist=[cls_name])
        registry.register_extractor(name, getattr(mod, cls_name))
    except ImportError:
        pass


def _try_register_chunker(registry: PluginRegistry, name: str, module: str, cls_name: str) -> None:
    try:
        mod = __import__(module, fromlist=[cls_name])
        registry.register_chunker(name, getattr(mod, cls_name))
    except ImportError:
        pass


def _try_register_reranker(registry: PluginRegistry, name: str, module: str, cls_name: str) -> None:
    try:
        mod = __import__(module, fromlist=[cls_name])
        registry.register_reranker(name, getattr(mod, cls_name))
    except ImportError:
        pass


def _try_register_evaluator(
    registry: PluginRegistry, name: str, module: str, cls_name: str
) -> None:
    try:
        mod = __import__(module, fromlist=[cls_name])
        registry.register_evaluator(name, getattr(mod, cls_name))
    except ImportError:
        pass


_register_builtins()


# --- Convenience functions ---


def parse(source: str, *, parser: str = "docling", **kwargs: object) -> ParsedDocument:
    """Parse a document using the specified parser."""
    from docpipe.parsers.router import resolve_parser

    name = resolve_parser(parser, source=source, tier=str(kwargs.pop("tier", "balanced")))
    p = PluginRegistry.get().get_parser(name, **kwargs)
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
