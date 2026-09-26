"""Category-specific, JSON-safe option envelopes for selected plugins."""

from __future__ import annotations

from docpipe.plugins.configuration import PluginConfig


class VectorStoreOptions(PluginConfig):
    """Vector provider name and options validated by its selected factory."""


class SourcePluginOptions(PluginConfig):
    """Source provider name and options validated by its selected factory."""
