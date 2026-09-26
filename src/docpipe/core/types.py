"""Compatibility exports for public domain schemas.

New code should import from the focused ``docpipe.core.schemas`` modules.
Existing SDK imports remain valid and resolve to the same model classes.
"""

from docpipe.core.schemas.common import TokenUsage, validate_table_name
from docpipe.core.schemas.documents import DocumentFormat, PageContent, ParsedDocument
from docpipe.core.schemas.evaluation import EvalConfig, EvalMetrics, EvalQuestion, EvalResult
from docpipe.core.schemas.extraction import ExtractionResult, ExtractionSchema, SourceSpan
from docpipe.core.schemas.ingestion import IngestionConfig, IngestionResult
from docpipe.core.schemas.pipeline import PipelineResult
from docpipe.core.schemas.rag import RAGChunk, RAGConfig, RAGResult

__all__ = [
    "DocumentFormat",
    "EvalConfig",
    "EvalMetrics",
    "EvalQuestion",
    "EvalResult",
    "ExtractionResult",
    "ExtractionSchema",
    "IngestionConfig",
    "IngestionResult",
    "PageContent",
    "ParsedDocument",
    "PipelineResult",
    "RAGChunk",
    "RAGConfig",
    "RAGResult",
    "SourceSpan",
    "TokenUsage",
    "validate_table_name",
]
