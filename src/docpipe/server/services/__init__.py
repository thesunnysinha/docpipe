"""HTTP-facing business logic — routers stay thin and delegate here."""

from docpipe.server.services.admin import AdminService
from docpipe.server.services.agents import AgentService
from docpipe.server.services.cost import CostService
from docpipe.server.services.discovery import DiscoveryService
from docpipe.server.services.documents import DocumentService
from docpipe.server.services.evaluate import EvaluateService
from docpipe.server.services.generate import GenerateService
from docpipe.server.services.ingest import IngestService
from docpipe.server.services.mcp import McpService
from docpipe.server.services.rag import RAGService
from docpipe.server.services.transcribe import TranscribeService

__all__ = [
    "AdminService",
    "AgentService",
    "CostService",
    "DiscoveryService",
    "DocumentService",
    "EvaluateService",
    "GenerateService",
    "IngestService",
    "McpService",
    "RAGService",
    "TranscribeService",
]
