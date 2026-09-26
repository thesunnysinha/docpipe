"""Exception hierarchy for docpipe."""

from docpipe.plugins.errors import PublicIntegrationError, RetryClassification


class DocpipeError(Exception):
    """Base exception for all docpipe errors."""


class ParserNotFoundError(DocpipeError):
    """Raised when a requested parser is not registered."""


class ExtractorNotFoundError(DocpipeError):
    """Raised when a requested extractor is not registered."""


class ParserNotInstalledError(DocpipeError):
    """Raised when a parser's underlying library is not installed."""


class ExtractorNotInstalledError(DocpipeError):
    """Raised when an extractor's underlying library is not installed."""


class ParseError(DocpipeError):
    """Raised when document parsing fails."""


class ExtractionError(DocpipeError):
    """Raised when structured extraction fails."""


class IngestionError(DocpipeError):
    """Raised when vector ingestion fails."""


class ConfigurationError(DocpipeError):
    """Raised for invalid configuration."""


class UnsupportedFormatError(DocpipeError):
    """Raised when a document format is not supported by the selected parser."""


class RAGError(DocpipeError):
    """Raised when RAG query or generation fails."""


class EvalError(DocpipeError):
    """Raised when evaluation fails."""


class TranscriptionError(DocpipeError):
    """Raised when speech-to-text transcription fails."""


class ChunkerNotFoundError(DocpipeError):
    """Raised when a requested chunker is not registered."""


class RerankerNotFoundError(DocpipeError):
    """Raised when a requested reranker is not registered."""


class EvaluatorNotFoundError(DocpipeError):
    """Raised when a requested evaluator is not registered."""


class OperationDeadlineExceededError(PublicIntegrationError):
    """Raised when an operation has no remaining execution time."""

    code = "operation_deadline_exceeded"
    default_retry = RetryClassification.NEVER
