"""Plugin registry for parsers, extractors, chunkers, rerankers, and evaluators."""

from __future__ import annotations

import importlib.metadata
import logging
import warnings
from typing import Any

from docpipe.core.errors import (
    ChunkerNotFoundError,
    EvaluatorNotFoundError,
    ExtractorNotFoundError,
    ParserNotFoundError,
    RerankerNotFoundError,
)
from docpipe.core.plugin_meta import plugin_info_dict

logger = logging.getLogger(__name__)
_LEGACY_WARNING_EMITTED = False

_ENTRYPOINT_GROUPS = (
    ("docpipe.parsers", "_parsers", "parser"),
    ("docpipe.extractors", "_extractors", "extractor"),
    ("docpipe.chunkers", "_chunkers", "chunker"),
    ("docpipe.rerankers", "_rerankers", "reranker"),
    ("docpipe.evaluators", "_evaluators", "evaluator"),
)


class PluginRegistry:
    """Deprecated compatibility registry for legacy plugin categories.

    Each instance owns its registrations. ``get`` exposes the process-default
    registry and discovers installed entry points lazily; new integrations
    should instead use the registry owned by a :class:`DocpipeRuntime`.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, type[Any]] = {}
        self._extractors: dict[str, type[Any]] = {}
        self._chunkers: dict[str, type[Any]] = {}
        self._rerankers: dict[str, type[Any]] = {}
        self._evaluators: dict[str, type[Any]] = {}
        self._discovered = False

    @classmethod
    def get(cls) -> PluginRegistry:
        """Return the deprecated process-default compatibility registry."""
        global _LEGACY_WARNING_EMITTED
        if not _LEGACY_WARNING_EMITTED:
            warnings.warn(
                "PluginRegistry.get() is deprecated; inject a DocpipeRuntime registry instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            _LEGACY_WARNING_EMITTED = True
        from docpipe.bootstrap.sdk import get_default_runtime

        registry = get_default_runtime().legacy_registry
        registry._ensure_discovered()
        return registry

    @classmethod
    def reset(cls) -> None:
        """Reset the deprecated process default when it is not active."""
        from docpipe.bootstrap.sdk import reset_default_runtime

        reset_default_runtime()

    def register_parser(self, name: str, parser_cls: type[Any]) -> None:
        """Register or replace a parser class under ``name`` on this instance."""
        self._parsers[name] = parser_cls

    def register_extractor(self, name: str, extractor_cls: type[Any]) -> None:
        """Register or replace an extractor class under ``name`` on this instance."""
        self._extractors[name] = extractor_cls

    def register_chunker(self, name: str, chunker_cls: type[Any]) -> None:
        """Register or replace a chunker class under ``name`` on this instance."""
        self._chunkers[name] = chunker_cls

    def register_reranker(self, name: str, reranker_cls: type[Any]) -> None:
        """Register or replace a reranker class under ``name`` on this instance."""
        self._rerankers[name] = reranker_cls

    def register_evaluator(self, name: str, evaluator_cls: type[Any]) -> None:
        """Register or replace an evaluator class under ``name`` on this instance."""
        self._evaluators[name] = evaluator_cls

    def get_parser(self, name: str, **kwargs: Any) -> Any:
        """Instantiate a registered parser, forwarding constructor options.

        Installed parser entry points are discovered on first lookup. Raises
        :class:`ParserNotFoundError` when ``name`` is not registered.
        """
        self._ensure_discovered()
        if name not in self._parsers:
            raise ParserNotFoundError(
                f"Parser '{name}' not found. Available: {list(self._parsers.keys())}"
            )
        return self._parsers[name](**kwargs)

    def get_extractor(self, name: str, **kwargs: Any) -> Any:
        """Instantiate a registered extractor with the supplied options.

        Raises :class:`ExtractorNotFoundError` when ``name`` is unknown.
        """
        self._ensure_discovered()
        if name not in self._extractors:
            raise ExtractorNotFoundError(
                f"Extractor '{name}' not found. Available: {list(self._extractors.keys())}"
            )
        return self._extractors[name](**kwargs)

    def get_chunker(self, name: str, **kwargs: Any) -> Any:
        """Instantiate a registered chunker with the supplied options.

        Raises :class:`ChunkerNotFoundError` when ``name`` is unknown.
        """
        self._ensure_discovered()
        if name not in self._chunkers:
            raise ChunkerNotFoundError(
                f"Chunker '{name}' not found. Available: {list(self._chunkers.keys())}"
            )
        return self._chunkers[name](**kwargs)

    def get_reranker(self, name: str, **kwargs: Any) -> Any:
        """Instantiate a registered reranker with the supplied options.

        Raises :class:`RerankerNotFoundError` when ``name`` is unknown.
        """
        self._ensure_discovered()
        if name not in self._rerankers:
            raise RerankerNotFoundError(
                f"Reranker '{name}' not found. Available: {list(self._rerankers.keys())}"
            )
        return self._rerankers[name](**kwargs)

    def get_evaluator(self, name: str, **kwargs: Any) -> Any:
        """Instantiate a registered evaluator with the supplied options.

        Raises :class:`EvaluatorNotFoundError` when ``name`` is unknown.
        """
        self._ensure_discovered()
        if name not in self._evaluators:
            raise EvaluatorNotFoundError(
                f"Evaluator '{name}' not found. Available: {list(self._evaluators.keys())}"
            )
        return self._evaluators[name](**kwargs)

    def list_parsers(self) -> list[str]:
        """Return parser names registered locally or through entry points."""
        self._ensure_discovered()
        return list(self._parsers.keys())

    def list_extractors(self) -> list[str]:
        """Return extractor names registered locally or through entry points."""
        self._ensure_discovered()
        return list(self._extractors.keys())

    def list_chunkers(self) -> list[str]:
        """Return chunker names registered locally or through entry points."""
        self._ensure_discovered()
        return list(self._chunkers.keys())

    def list_rerankers(self) -> list[str]:
        """Return reranker names registered locally or through entry points."""
        self._ensure_discovered()
        return list(self._rerankers.keys())

    def list_evaluators(self) -> list[str]:
        """Return evaluator names registered locally or through entry points."""
        self._ensure_discovered()
        return list(self._evaluators.keys())

    def parser_info(self, name: str) -> dict[str, Any]:
        """Return descriptive metadata for a parser or raise if it is unknown."""
        self._ensure_discovered()
        if name not in self._parsers:
            raise ParserNotFoundError(f"Parser '{name}' not found.")
        return plugin_info_dict(self._parsers[name], name=name)

    def extractor_info(self, name: str) -> dict[str, Any]:
        """Return descriptive metadata for an extractor or raise if unknown."""
        self._ensure_discovered()
        if name not in self._extractors:
            raise ExtractorNotFoundError(f"Extractor '{name}' not found.")
        return plugin_info_dict(self._extractors[name], name=name)

    def chunker_info(self, name: str) -> dict[str, Any]:
        """Return descriptive metadata for a chunker or raise if it is unknown."""
        self._ensure_discovered()
        if name not in self._chunkers:
            raise ChunkerNotFoundError(f"Chunker '{name}' not found.")
        return plugin_info_dict(self._chunkers[name], name=name)

    def reranker_info(self, name: str) -> dict[str, Any]:
        """Return descriptive metadata for a reranker or raise if it is unknown."""
        self._ensure_discovered()
        if name not in self._rerankers:
            raise RerankerNotFoundError(f"Reranker '{name}' not found.")
        return plugin_info_dict(self._rerankers[name], name=name)

    def evaluator_info(self, name: str) -> dict[str, Any]:
        """Return descriptive metadata for an evaluator or raise if unknown."""
        self._ensure_discovered()
        if name not in self._evaluators:
            raise EvaluatorNotFoundError(f"Evaluator '{name}' not found.")
        return plugin_info_dict(self._evaluators[name], name=name)

    def all_plugins(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Return introspection payload for GET /plugins."""
        return {
            "parsers": {n: self.parser_info(n) for n in self.list_parsers()},
            "extractors": {n: self.extractor_info(n) for n in self.list_extractors()},
            "chunkers": {n: self.chunker_info(n) for n in self.list_chunkers()},
            "rerankers": {n: self.reranker_info(n) for n in self.list_rerankers()},
            "evaluators": {n: self.evaluator_info(n) for n in self.list_evaluators()},
        }

    def _ensure_discovered(self) -> None:
        if self._discovered:
            return
        self._discovered = True
        self._discover_entrypoints()

    def _discover_entrypoints(self) -> None:
        for group, attr, kind in _ENTRYPOINT_GROUPS:
            store: dict[str, type[Any]] = getattr(self, attr)
            for ep in importlib.metadata.entry_points(group=group):
                if ep.name in store:
                    continue
                try:
                    cls = ep.load()
                    store[ep.name] = cls
                    logger.debug("Registered %s plugin: %s", kind, ep.name)
                except Exception as exc:
                    logger.warning(
                        "legacy.plugin.load.failed",
                        extra={
                            "event": "legacy.plugin.load.failed",
                            "plugin_kind": kind,
                            "plugin": ep.name,
                            "error_type": type(exc).__name__,
                        },
                    )
