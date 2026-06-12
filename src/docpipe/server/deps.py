"""FastAPI dependencies for the docpipe server."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from docpipe.config import get_settings
from docpipe.config.settings import DocpipeSettings
from docpipe.registry.registry import PluginRegistry
from docpipe.server.auth import require_auth
from docpipe.server.services import (
    AgentService,
    DiscoveryService,
    DocumentService,
    EvaluateService,
    GenerateService,
    IngestService,
    RAGService,
    TranscribeService,
)

Auth = Annotated[None, Depends(require_auth)]


def get_app_settings() -> DocpipeSettings:
    return get_settings()


def get_registry() -> PluginRegistry:
    return PluginRegistry.get()


SettingsDep = Annotated[DocpipeSettings, Depends(get_app_settings)]
RegistryDep = Annotated[PluginRegistry, Depends(get_registry)]


def get_discovery_service(
    settings: SettingsDep,
    registry: RegistryDep,
) -> DiscoveryService:
    return DiscoveryService(settings, registry)


def get_document_service(registry: RegistryDep) -> DocumentService:
    return DocumentService(registry)


def get_ingest_service(settings: SettingsDep, registry: RegistryDep) -> IngestService:
    return IngestService(settings, registry)


def get_rag_service(settings: SettingsDep) -> RAGService:
    return RAGService(settings)


def get_agent_service(settings: SettingsDep) -> AgentService:
    return AgentService(settings)


def get_evaluate_service(settings: SettingsDep) -> EvaluateService:
    return EvaluateService(settings)


def get_generate_service() -> GenerateService:
    return GenerateService()


def get_transcribe_service(settings: SettingsDep) -> TranscribeService:
    return TranscribeService(settings)


DiscoveryServiceDep = Annotated[DiscoveryService, Depends(get_discovery_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
IngestServiceDep = Annotated[IngestService, Depends(get_ingest_service)]
RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]
AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
EvaluateServiceDep = Annotated[EvaluateService, Depends(get_evaluate_service)]
GenerateServiceDep = Annotated[GenerateService, Depends(get_generate_service)]
TranscribeServiceDep = Annotated[TranscribeService, Depends(get_transcribe_service)]
