"""Configuration schema metadata must remain operator-friendly."""

from docpipe.config.settings import DocpipeSettings
from docpipe.core.schemas.rag import RAGChunk, RAGConfig, RAGResult
from docpipe.plugins.manifest_models import PluginManifest, PluginManifestEntry


def should_describe_every_operator_setting_in_generated_schema() -> None:
    """Document all settings so generated schema and env references explain them."""
    undocumented = [
        name for name, field in DocpipeSettings.model_fields.items() if not field.description
    ]

    assert undocumented == []


def should_describe_every_rag_schema_field() -> None:
    """Document RAG request and result fields in generated schema metadata."""
    models = (RAGConfig, RAGChunk, RAGResult)
    undocumented = [
        f"{model.__name__}.{name}"
        for model in models
        for name, field in model.model_fields.items()
        if not field.description
    ]

    assert undocumented == []


def should_describe_every_plugin_manifest_field() -> None:
    """Give plugin authors useful generated schema guidance for manifest fields."""
    models = (PluginManifest, PluginManifestEntry)
    undocumented = [
        f"{model.__name__}.{name}"
        for model in models
        for name, field in model.model_fields.items()
        if not field.description
    ]

    assert undocumented == []
