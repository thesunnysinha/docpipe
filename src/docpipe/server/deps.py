"""FastAPI dependencies for the docpipe server."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from docpipe.bootstrap.runtime import DocpipeRuntime
from docpipe.config.settings import DocpipeSettings
from docpipe.registry.registry import PluginRegistry
from docpipe.server.auth import require_auth
from docpipe.server.services import (
    AdminService,
    AgentService,
    CostService,
    DiscoveryService,
    DocumentService,
    EvaluateService,
    GenerateService,
    IngestService,
    McpService,
    RAGService,
    TranscribeService,
)

Auth = Annotated[None, Depends(require_auth)]


def get_runtime(request: Request) -> DocpipeRuntime:
    """Return the application-scoped runtime attached during composition."""
    runtime: DocpipeRuntime = request.app.state.docpipe_runtime
    return runtime


RuntimeDep = Annotated[DocpipeRuntime, Depends(get_runtime)]


def get_app_settings(runtime: RuntimeDep) -> DocpipeSettings:
    """Return settings owned by the application runtime."""
    return runtime.settings


def get_registry(runtime: RuntimeDep) -> PluginRegistry:
    """Return the isolated legacy registry during its migration window."""
    return runtime.legacy_registry


SettingsDep = Annotated[DocpipeSettings, Depends(get_app_settings)]
RegistryDep = Annotated[PluginRegistry, Depends(get_registry)]


def get_admin_service() -> AdminService:
    """Create the admin service used by the current request."""
    return AdminService()


def get_discovery_service(
    settings: SettingsDep,
    registry: RegistryDep,
    runtime: RuntimeDep,
) -> DiscoveryService:
    """Build discovery logic from the request's runtime-owned settings and registry."""
    return DiscoveryService(settings, registry, runtime)


def get_document_service(
    settings: SettingsDep,
    registry: RegistryDep,
    runtime: RuntimeDep,
) -> DocumentService:
    """Build document operations against the application's legacy registry."""
    return DocumentService(settings, registry, runtime)


def get_ingest_service(
    settings: SettingsDep,
    registry: RegistryDep,
    runtime: RuntimeDep,
) -> IngestService:
    """Build ingestion operations from the current application dependencies."""
    return IngestService(settings, registry, runtime)


def get_rag_service(request: Request, settings: SettingsDep, runtime: RuntimeDep) -> RAGService:
    """Inject the one application-owned cache into request-scoped services."""
    return RAGService(settings, runtime, getattr(request.app.state, "rag_cache", None))


def get_agent_service(settings: SettingsDep) -> AgentService:
    """Create the agent service using the application's resolved settings."""
    return AgentService(settings)


def get_evaluate_service(settings: SettingsDep) -> EvaluateService:
    """Create the evaluation service using the application's resolved settings."""
    return EvaluateService(settings)


def get_generate_service() -> GenerateService:
    """Create the stateless generate service for dependency injection."""
    return GenerateService()


def get_transcribe_service(settings: SettingsDep) -> TranscribeService:
    """Create the transcription service using the application's resolved settings."""
    return TranscribeService(settings)


def get_cost_service() -> CostService:
    """Create the cost service used by cost-reporting routes."""
    return CostService()


AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]
DiscoveryServiceDep = Annotated[DiscoveryService, Depends(get_discovery_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
IngestServiceDep = Annotated[IngestService, Depends(get_ingest_service)]
RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]
AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
EvaluateServiceDep = Annotated[EvaluateService, Depends(get_evaluate_service)]
GenerateServiceDep = Annotated[GenerateService, Depends(get_generate_service)]
TranscribeServiceDep = Annotated[TranscribeService, Depends(get_transcribe_service)]
CostServiceDep = Annotated[CostService, Depends(get_cost_service)]


def get_mcp_service(
    document_service: DocumentServiceDep,
    rag_service: RAGServiceDep,
) -> McpService:
    """Compose MCP operations from the same document and RAG services as HTTP routes."""
    return McpService(document_service, rag_service)


McpServiceDep = Annotated[McpService, Depends(get_mcp_service)]
