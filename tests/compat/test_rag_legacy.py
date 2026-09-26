"""Public RAG facade snapshots over a real selected vector plugin."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docpipe.bootstrap.runtime import DocpipeRuntime, build_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.core.types import RAGConfig, TokenUsage
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.contracts.vectorstore import CollectionRef, VectorRecord, WriteBatch
from docpipe.plugins.descriptors import PluginCategory
from docpipe.rag.pipeline import RAGPipeline

pytest.importorskip("turbovec")


def _config(index_root: Path, **overrides: object) -> RAGConfig:
    values: dict[str, object] = {
        "connection_string": "postgresql://test/db",
        "table_name": "documents",
        "embedding_provider": "openai",
        "embedding_model": "embedding",
        "llm_provider": "openai",
        "llm_model": "model",
        "system_prompt": "Context: {context} Question: {question}",
        "vector_backend": "turbovec",
        "turbovec_index_dir": str(index_root),
    }
    values.update(overrides)
    return RAGConfig.model_validate(values)


def _embeddings() -> MagicMock:
    embeddings = MagicMock()
    embeddings.embed_query.return_value = [1.0] + [0.0] * 7
    embeddings.embed_documents.return_value = [[1.0] + [0.0] * 7]
    return embeddings


def _model() -> MagicMock:
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(
        content="Public answer",
        usage_metadata={"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
    )
    llm.stream.return_value = iter(
        [
            MagicMock(content="Public"),
            MagicMock(
                content=" answer",
                usage_metadata={"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
            ),
        ]
    )
    return llm


async def _seed_collection(runtime: DocpipeRuntime, index_root: Path) -> None:
    adapter = runtime.loader.load(PluginCategory.VECTORSTORE, "turbovec").create(
        PluginConfig(
            provider="turbovec",
            options={"index_root": str(index_root), "collection": "documents"},
        ),
        context=runtime.factory_context(),
    )
    binding = adapter.binding
    assert binding.admin is not None and binding.writer is not None
    await binding.admin.ensure_collection(CollectionRef("documents"), 8)
    await binding.writer.upsert(
        WriteBatch(
            CollectionRef("documents"),
            (
                VectorRecord(
                    "id-1",
                    "stored context",
                    (1.0, *([0.0] * 7)),
                    {"source": "report.pdf", "page": 3},
                    "report.pdf",
                ),
            ),
        )
    )


@pytest.mark.asyncio
async def test_public_facade_preserves_citations_scores_usage_and_stream(
    tmp_path: Path,
) -> None:
    settings = DocpipeSettings.model_construct(max_concurrency=2, disabled_plugins=None)
    runtime = build_runtime(settings)
    config = _config(tmp_path)
    with (
        patch.object(RAGPipeline, "_create_embeddings", return_value=_embeddings()),
        patch.object(RAGPipeline, "_create_llm", return_value=_model()),
    ):
        async with runtime:
            await _seed_collection(runtime, tmp_path)
            pipeline = RAGPipeline(config, runtime=runtime)
            answer = await pipeline.aquery("What happened?")

    assert answer.answer == "Public answer"
    assert answer.sources == ["report.pdf"]
    assert answer.chunks[0].page == 3
    assert answer.chunks[0].score > 0
    assert answer.usage == TokenUsage(input_tokens=4, output_tokens=2, total_tokens=6)


def test_sync_stream_preserves_incremental_tokens_and_usage(tmp_path: Path) -> None:
    async def seed() -> None:
        runtime = build_runtime(
            DocpipeSettings.model_construct(max_concurrency=2, disabled_plugins=None)
        )
        async with runtime:
            await _seed_collection(runtime, tmp_path)

    asyncio.run(seed())
    with (
        patch.object(RAGPipeline, "_create_embeddings", return_value=_embeddings()),
        patch.object(RAGPipeline, "_create_llm", return_value=_model()),
    ):
        pipeline = RAGPipeline(_config(tmp_path, stream=True))
        tokens = list(pipeline.stream_query("What happened?"))
    assert tokens == ["Public", " answer"]
    assert pipeline.last_usage is not None and pipeline.last_usage.total_tokens == 6


@pytest.mark.asyncio
async def test_cache_hit_skips_generation_and_config_change_invalidates(
    tmp_path: Path,
) -> None:
    runtime = build_runtime(
        DocpipeSettings.model_construct(max_concurrency=2, disabled_plugins=None)
    )
    model = _model()
    with (
        patch.object(RAGPipeline, "_create_embeddings", return_value=_embeddings()),
        patch.object(RAGPipeline, "_create_llm", return_value=model),
    ):
        async with runtime:
            await _seed_collection(runtime, tmp_path)
            pipeline = RAGPipeline(_config(tmp_path, cache_enabled=True), runtime=runtime)
            first = await pipeline.aquery("question")
            second = await pipeline.aquery("question")
            pipeline._config.top_k = 2
            third = await pipeline.aquery("question")

    assert first.answer == second.answer == third.answer
    assert first is not second
    assert model.invoke.call_count == 2
    assert len(pipeline._cache) == 2
