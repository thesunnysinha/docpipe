"""HTTP API request/response schemas for the docpipe server."""

from docpipe.schemas.agents import AgentQueryRequest, AgentQueryResponse
from docpipe.schemas.base import ApiRequest, ApiResponse
from docpipe.schemas.cost import CostEstimateRequest, CostEstimateResponse
from docpipe.schemas.delete import DeleteRequest, DeleteResponse
from docpipe.schemas.evaluate import EvaluateRequest, EvaluateResponse
from docpipe.schemas.extract import ExtractRequest, ExtractResponse
from docpipe.schemas.generate import GenerateRequest, GenerateResponse
from docpipe.schemas.health import DependencyStatus, HealthResponse
from docpipe.schemas.ingest import IngestRequest, IngestResponse
from docpipe.schemas.mcp import McpCallRequest, McpCallResponse, McpToolDescriptor, McpToolsResponse
from docpipe.schemas.parse import ParseRequest, ParseResponse
from docpipe.schemas.plugins import PluginInfo, PluginsResponse
from docpipe.schemas.profiles import (
    PluginResolveRequest,
    PluginResolveResponse,
    ProfilesResponse,
    RecommendedPlugins,
)
from docpipe.schemas.rag import (
    ChatMessage,
    RAGChunkResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from docpipe.schemas.run import RunRequest, RunResponse
from docpipe.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from docpipe.schemas.sources import ListSourcesRequest, ListSourcesResponse, SourceSummary
from docpipe.schemas.transcribe import TranscribeResponse

__all__ = [
    "AgentQueryRequest",
    "AgentQueryResponse",
    "ApiRequest",
    "ApiResponse",
    "ChatMessage",
    "CostEstimateRequest",
    "CostEstimateResponse",
    "DeleteRequest",
    "DeleteResponse",
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
    "McpCallRequest",
    "McpCallResponse",
    "McpToolDescriptor",
    "McpToolsResponse",
    "ParseRequest",
    "ParseResponse",
    "PluginInfo",
    "PluginResolveRequest",
    "PluginResolveResponse",
    "PluginsResponse",
    "ProfilesResponse",
    "RAGChunkResponse",
    "RAGQueryRequest",
    "RAGQueryResponse",
    "RecommendedPlugins",
    "RunRequest",
    "RunResponse",
    "SearchRequest",
    "SearchResponse",
    "SearchResultItem",
    "SourceSummary",
    "TranscribeResponse",
]
