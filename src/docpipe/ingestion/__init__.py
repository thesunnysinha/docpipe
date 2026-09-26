"""Vendor-neutral ingestion orchestration and compatibility facade."""

from docpipe.ingestion.configuration import (
    IncrementalFailureMode,
    IngestionOptions,
    IngestMode,
)
from docpipe.ingestion.contextualization import ContextGenerator, Contextualizer
from docpipe.ingestion.coordinator import (
    IncompleteIngestionError,
    IngestionChunker,
    IngestionCoordinator,
    IngestionDocumentBuilder,
)
from docpipe.ingestion.document_builder import DocumentBuilder, IngestionDocument
from docpipe.ingestion.incremental import (
    IncrementalDecider,
    IncrementalState,
    IncrementalStateError,
)
from docpipe.ingestion.pipeline import IngestionPipeline

__all__ = [
    "ContextGenerator",
    "Contextualizer",
    "DocumentBuilder",
    "IncompleteIngestionError",
    "IncrementalDecider",
    "IncrementalFailureMode",
    "IncrementalState",
    "IncrementalStateError",
    "IngestMode",
    "IngestionChunker",
    "IngestionCoordinator",
    "IngestionDocument",
    "IngestionDocumentBuilder",
    "IngestionOptions",
    "IngestionPipeline",
]
