"""Exception hierarchy for docpipe."""


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
