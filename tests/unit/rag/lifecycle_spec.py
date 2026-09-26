"""Cancellation releases operation-owned vector plugins, not app runtimes."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.core.types import RAGConfig
from docpipe.plugins.contracts.vectorstore import VectorCapability, VectorStoreBinding
from docpipe.plugins.loader import PluginLoader
from docpipe.rag.pipeline import RAGPipeline


class WaitingReader:
    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def search(self, query: object) -> tuple[object, ...]:
        self.started.set()
        await asyncio.Event().wait()
        return ()

    async def aggregate_sources(self, collection: object) -> tuple[object, ...]:
        return ()


class ManagedPlugin:
    def __init__(self, reader: WaitingReader) -> None:
        self.binding = VectorStoreBinding(frozenset({VectorCapability.DENSE_SEARCH}), reader=reader)
        self.closed = False

    async def __aenter__(self) -> ManagedPlugin:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        self.closed = True


def _config() -> RAGConfig:
    return RAGConfig(
        connection_string="postgresql://test/db",
        table_name="documents",
        embedding_provider="openai",
        embedding_model="model",
        llm_provider="openai",
        llm_model="model",
        system_prompt="{context} {question}",
    )


@pytest.mark.asyncio
async def test_cancelled_query_closes_selected_plugin_and_preserves_app_runtime() -> None:
    runtime = build_runtime(
        DocpipeSettings.model_construct(max_concurrency=2, disabled_plugins=None)
    )
    reader = WaitingReader()
    plugin = ManagedPlugin(reader)
    embeddings = MagicMock()
    embeddings.embed_query.return_value = [1.0] * 8
    with (
        patch.object(RAGPipeline, "_create_embeddings", return_value=embeddings),
        patch.object(RAGPipeline, "_create_llm", return_value=MagicMock()),
        patch.object(PluginLoader, "load") as load,
    ):
        load.return_value.create.return_value = plugin
        async with runtime:
            task = asyncio.create_task(RAGPipeline(_config(), runtime=runtime).aquery("private"))
            await asyncio.wait_for(reader.started.wait(), timeout=2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert plugin.closed
            assert runtime.is_active
