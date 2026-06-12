"""Discovery endpoints: homepage, health, plugins, profiles."""

from __future__ import annotations

from fastapi.responses import HTMLResponse

from docpipe._version import __version__
from docpipe.config.settings import DocpipeSettings
from docpipe.profiles.catalog import INSTALL_PROFILES
from docpipe.profiles.guardrails import build_plugins_payload
from docpipe.profiles.presets import list_runtime_presets
from docpipe.profiles.resolve import resolve_recommendation
from docpipe.registry.registry import PluginRegistry
from docpipe.schemas import (
    HealthResponse,
    PluginResolveRequest,
    PluginResolveResponse,
    ProfilesResponse,
)
from docpipe.schemas.plugins import PluginsResponse
from docpipe.server.health import build_health_response
from docpipe.server.homepage import render_homepage


class DiscoveryService:
    def __init__(self, settings: DocpipeSettings, registry: PluginRegistry) -> None:
        self._settings = settings
        self._registry = registry

    def homepage(self) -> HTMLResponse:
        preset_catalog = list_runtime_presets()
        html = render_homepage(
            version=__version__,
            profile=self._settings.profile,
            presets=[{"name": name, **meta} for name, meta in preset_catalog.items()],
            parsers=self._registry.list_parsers(),
            extractors=self._registry.list_extractors(),
        )
        return HTMLResponse(content=html)

    def health(self) -> HealthResponse:
        return build_health_response(
            __version__,
            {
                "parsers": self._registry.list_parsers(),
                "extractors": self._registry.list_extractors(),
            },
        )

    def list_plugins(self) -> PluginsResponse:
        """Return the full plugin catalog with tier and allowlist metadata."""
        return PluginsResponse.from_payload(build_plugins_payload())

    def list_profiles(self) -> ProfilesResponse:
        return ProfilesResponse(
            install_profile=self._settings.profile,
            install_profiles=INSTALL_PROFILES,
            runtime_presets=list_runtime_presets(),
            server_defaults={
                "default_parser": self._settings.default_parser,
                "default_parser_tier": self._settings.default_parser_tier,
                "default_chunker": self._settings.default_chunker,
                "default_reranker": self._settings.default_reranker,
                "default_rag_strategy": self._settings.default_rag_strategy,
                "default_runtime_preset": self._settings.default_runtime_preset,
            },
        )

    def resolve_plugins(self, req: PluginResolveRequest) -> PluginResolveResponse:
        data = resolve_recommendation(
            source=req.source,
            goal=req.goal,
            preset=req.preset,
        )
        return PluginResolveResponse.model_validate(data)
