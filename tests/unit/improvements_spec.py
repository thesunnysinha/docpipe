"""Legacy configuration, contextual chunk, and chunk-method regressions."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from docpipe.core.types import IngestionConfig, RAGConfig
from docpipe.ingestion.pipeline import IngestionPipeline
from docpipe.rag.pipeline import RAGPipeline


def _ingestion_config(**overrides: object) -> IngestionConfig:
    values: dict[str, object] = {
        "connection_string": "postgresql://test/db",
        "table_name": "documents",
        "embedding_provider": "openai",
        "embedding_model": "model",
    }
    values.update(overrides)
    return IngestionConfig.model_validate(values)


def test_contextual_injection_disabled_by_default() -> None:
    assert _ingestion_config().contextual_injection is False


def test_inject_context_prepends_sentence() -> None:
    model = MagicMock()
    model.invoke.return_value.content = "This chunk discusses X."
    chunk = MagicMock(page_content="Original chunk content.")

    IngestionPipeline._inject_context([chunk], "Full doc text.", model)

    assert chunk.page_content == "This chunk discusses X.\n\nOriginal chunk content."


def test_semantic_cache_is_opt_in_and_cosine_handles_zero_vectors() -> None:
    config = RAGConfig(
        connection_string="postgresql://test/db",
        table_name="documents",
        embedding_provider="openai",
        embedding_model="model",
        llm_provider="openai",
        llm_model="model",
    )
    assert config.cache_enabled is False
    assert config.cache_similarity_threshold == 0.95
    assert config.cache_max_size == 100
    assert RAGPipeline._cosine_sim((1.0, 0.0), (1.0, 0.0)) == pytest.approx(1.0)
    assert RAGPipeline._cosine_sim((1.0, 0.0), (0.0, 1.0)) == 0.0
    assert RAGPipeline._cosine_sim((0.0, 0.0), (1.0, 0.0)) == 0.0


@pytest.mark.parametrize(
    "method,size",
    [
        ("paper", 1500),
        ("laws", 2000),
        ("book", 2000),
        ("qa", 500),
        ("manual", 800),
        ("table", 500),
        ("presentation", 600),
    ],
)
def test_domain_chunk_methods_have_stable_sizes(method: str, size: int) -> None:
    splitter = IngestionPipeline._create_splitter(_ingestion_config(chunk_method=method))
    assert splitter._chunk_size == size


def test_default_chunk_method_uses_requested_size_and_overlap() -> None:
    splitter = IngestionPipeline._create_splitter(
        _ingestion_config(chunk_size=500, chunk_overlap=50)
    )
    assert (splitter._chunk_size, splitter._chunk_overlap) == (500, 50)


def test_paper_separators_include_heading() -> None:
    splitter = IngestionPipeline._create_splitter(_ingestion_config(chunk_method="paper"))
    assert "\n## " in splitter._separators


def test_table_has_zero_overlap() -> None:
    splitter = IngestionPipeline._create_splitter(_ingestion_config(chunk_method="table"))
    assert splitter._chunk_overlap == 0


def test_presentation_splits_on_slide_divider() -> None:
    splitter = IngestionPipeline._create_splitter(_ingestion_config(chunk_method="presentation"))
    assert "\n---" in splitter._separators
