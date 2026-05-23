"""HTTP API request/response schemas for the docpipe server."""

from docpipe.schemas.evaluate import EvaluateRequest, EvaluateResponse
from docpipe.schemas.extract import ExtractRequest, ExtractResponse
from docpipe.schemas.generate import GenerateRequest, GenerateResponse
from docpipe.schemas.health import DependencyStatus, HealthResponse
from docpipe.schemas.ingest import IngestRequest, IngestResponse
from docpipe.schemas.parse import ParseRequest, ParseResponse
from docpipe.schemas.rag import RAGChunkResponse, RAGQueryRequest, RAGQueryResponse
from docpipe.schemas.run import RunRequest
from docpipe.schemas.search import SearchRequest, SearchResponse
from docpipe.schemas.sources import ListSourcesRequest, ListSourcesResponse, SourceSummary
from docpipe.schemas.transcribe import TranscribeResponse

__all__ = [
    "DependencyStatus",
    "EvaluateRequest",
    "EvaluateResponse",
    "ExtractRequest",
    "ExtractResponse",
    "GenerateRequest",
    "GenerateResponse",
    "HealthResponse",
    "IngestRequest",
    "IngestResponse",
    "ListSourcesRequest",
    "ListSourcesResponse",
    "ParseRequest",
    "ParseResponse",
    "RAGChunkResponse",
    "RAGQueryRequest",
    "RAGQueryResponse",
    "RunRequest",
    "SearchRequest",
    "SearchResponse",
    "SourceSummary",
    "TranscribeResponse",
]
