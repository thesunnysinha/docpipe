"""Application mapping, warnings, selected factories, and cache isolation."""

from __future__ import annotations

import warnings

import pytest

from docpipe.config.compatibility import warn_legacy_field_once
from docpipe.config.plugin_options import VectorStoreOptions
from docpipe.config.settings import DocpipeSettings
from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.core.errors import ConfigurationError
from docpipe.core.types import IngestionConfig, RAGConfig
from docpipe.ingestion.composition import _vector_plugin_config as ingestion_vector_config
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.errors import PluginConfigurationError
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.rag.cache import cache_namespace
from docpipe.rag.composition import _vector_plugin_config as rag_vector_config
from docpipe.schemas.ingest import IngestRequest
from docpipe.server.request_mapping import vector_fields_from_request
from docpipe.vectorstores.turbovec.factory import create_plugin as create_turbovec


def should_warn_once_per_legacy_field_without_values() -> None:
    field = "deprecated_field_for_test"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warn_legacy_field_once(field)
        warn_legacy_field_once(field)
    assert len(caught) == 1
    assert field in str(caught[0].message)


def should_prefer_namespaced_vector_provider_in_request_mapping() -> None:
    request = IngestRequest.model_validate(
        {
            "source": "/reports/one.pdf",
            "connection_string": "postgresql://legacy/db",
            "table_name": "docs",
            "embedding_provider": "openai",
            "embedding_model": "model",
            "vector_store": {
                "provider": "qdrant",
                "options": {"url": "https://vectors.example", "collection": "docs"},
            },
        }
    )
    fields = vector_fields_from_request(request, DocpipeSettings())
    assert fields["vector_store"].provider == "qdrant"
    assert fields["vector_backend"] is None


def should_reject_new_provider_in_legacy_vector_field() -> None:
    request = IngestRequest.model_validate(
        {
            "source": "/reports/one.pdf",
            "connection_string": "postgresql://db/docs",
            "table_name": "docs",
            "embedding_provider": "openai",
            "embedding_model": "model",
            "vector_backend": "qdrant",
        }
    )
    with pytest.raises(ConfigurationError, match="vector_backend"):
        vector_fields_from_request(request, DocpipeSettings())


def should_pass_selected_options_through_ingestion_and_rag() -> None:
    selected = VectorStoreOptions(
        provider="qdrant", options={"url": "https://vectors.example", "collection": "docs"}
    )
    ingestion = IngestionConfig(
        connection_string="legacy-unused",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="model",
        vector_store=selected,
    )
    rag = RAGConfig(
        connection_string="legacy-unused",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="model",
        llm_provider="openai",
        llm_model="model",
        vector_store=selected,
    )
    assert ingestion_vector_config(ingestion, "qdrant").options == selected.options
    assert rag_vector_config(rag, "qdrant").options == selected.options


def should_report_selected_factory_option_path() -> None:
    envelope = PluginConfig(
        provider="turbovec", options={"collection": "docs", "future_option": True}
    )
    with pytest.raises(PluginConfigurationError) as failure:
        create_turbovec(
            envelope, context=PluginFactoryContext(blocking_runner=BoundedBlockingRunner(1))
        )
    assert failure.value.context["field"] == "vector_store.options.future_option"


def should_isolate_rag_cache_by_selected_vector_endpoint() -> None:
    def rag(url: str) -> RAGConfig:
        return RAGConfig(
            connection_string="legacy-unused",
            table_name="docs",
            embedding_provider="openai",
            embedding_model="model",
            llm_provider="openai",
            llm_model="model",
            vector_store=VectorStoreOptions(
                provider="qdrant", options={"url": url, "collection": "docs"}
            ),
        )

    assert cache_namespace(rag("https://one.example")) != cache_namespace(
        rag("https://two.example")
    )
