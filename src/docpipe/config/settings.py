"""Public composition root for Docpipe's modular settings models."""

from docpipe.config.settings_sections.admin import AdminSettings
from docpipe.config.settings_sections.base import Settings
from docpipe.config.settings_sections.core import CoreSettings
from docpipe.config.settings_sections.integrations import IntegrationSettings
from docpipe.config.settings_sections.mcp import MCPSettings
from docpipe.config.settings_sections.rag_cache import RAGCacheSettings
from docpipe.config.settings_sections.security import SecuritySettings
from docpipe.config.settings_sections.sources import SourceSettings


class DocpipeSettings(
    CoreSettings,
    RAGCacheSettings,
    MCPSettings,
    SourceSettings,
    SecuritySettings,
    IntegrationSettings,
    AdminSettings,
):
    """Combined settings model preserving Docpipe's flat, backwards-compatible API."""


__all__ = ["DocpipeSettings", "Settings"]
