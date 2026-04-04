"""Plugin registry for parsers and extractors."""

from __future__ import annotations

import importlib.metadata
import logging
from typing import Any

from docpipe.core.errors import ExtractorNotFoundError, ParserNotFoundError

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for parsers and extractors.

    Supports three registration methods:
    1. Explicit: registry.register_parser("name", ParserClass)
    2. Built-in: auto-registered during package init
    3. Entry-point: third-party packages discovered via pip entry points
    """

    _instance: PluginRegistry | None = None

    def __init__(self) -> None:
        self._parsers: dict[str, type[Any]] = {}
        self._extractors: dict[str, type[Any]] = {}
        self._discovered = False

    @classmethod
    def get(cls) -> PluginRegistry:
        """Get or create the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        if not cls._instance._discovered:
            cls._instance._discover_entrypoints()
            cls._instance._discovered = True
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None

    def register_parser(self, name: str, parser_cls: type[Any]) -> None:
        """Register a parser class by name."""
        self._parsers[name] = parser_cls
        logger.debug("Registered parser: %s", name)

    def register_extractor(self, name: str, extractor_cls: type[Any]) -> None:
        """Register an extractor class by name."""
        self._extractors[name] = extractor_cls
        logger.debug("Registered extractor: %s", name)

    def get_parser(self, name: str, **kwargs: Any) -> Any:
        """Get a parser instance by name."""
        if name not in self._parsers:
            raise ParserNotFoundError(
                f"Parser '{name}' not found. Available: {list(self._parsers.keys())}"
            )
        cls = self._parsers[name]
        return cls(**kwargs)

    def get_extractor(self, name: str, **kwargs: Any) -> Any:
        """Get an extractor instance by name."""
        if name not in self._extractors:
            raise ExtractorNotFoundError(
                f"Extractor '{name}' not found. Available: {list(self._extractors.keys())}"
            )
        cls = self._extractors[name]
        return cls(**kwargs)

    def list_parsers(self) -> list[str]:
        """List all registered parser names."""
        return list(self._parsers.keys())

    def list_extractors(self) -> list[str]:
        """List all registered extractor names."""
        return list(self._extractors.keys())

    def parser_info(self, name: str) -> dict[str, Any]:
        """Get info about a registered parser."""
        if name not in self._parsers:
            raise ParserNotFoundError(f"Parser '{name}' not found.")
        cls = self._parsers[name]
        return {
            "name": name,
            "class": f"{cls.__module__}.{cls.__qualname__}",
            "available": cls.is_available() if hasattr(cls, "is_available") else None,
            "formats": cls.supported_formats() if hasattr(cls, "supported_formats") else None,
        }

    def extractor_info(self, name: str) -> dict[str, Any]:
        """Get info about a registered extractor."""
        if name not in self._extractors:
            raise ExtractorNotFoundError(f"Extractor '{name}' not found.")
        cls = self._extractors[name]
        return {
            "name": name,
            "class": f"{cls.__module__}.{cls.__qualname__}",
            "available": cls.is_available() if hasattr(cls, "is_available") else None,
        }

    def _discover_entrypoints(self) -> None:
        """Auto-discover plugins via entry points."""
        for ep in importlib.metadata.entry_points(group="docpipe.parsers"):
            if ep.name not in self._parsers:
                try:
                    cls = ep.load()
                    self.register_parser(ep.name, cls)
                except Exception as e:
                    logger.warning("Failed to load parser plugin '%s': %s", ep.name, e)

        for ep in importlib.metadata.entry_points(group="docpipe.extractors"):
            if ep.name not in self._extractors:
                try:
                    cls = ep.load()
                    self.register_extractor(ep.name, cls)
                except Exception as e:
                    logger.warning("Failed to load extractor plugin '%s': %s", ep.name, e)
