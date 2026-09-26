"""Backward-compatible facade over the vendor-neutral ingestion coordinator."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import cast

from docpipe.bootstrap.runtime import DocpipeRuntime, build_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.core.errors import ConfigurationError, IngestionError
from docpipe.core.types import ExtractionResult, IngestionConfig, IngestionResult, ParsedDocument
from docpipe.ingestion.composition import build_ingestion_coordinator
from docpipe.ingestion.contextualization import ContextualInjector
from docpipe.ingestion.legacy import (
    LangChainContextGenerator,
    LegacyLlm,
    create_chunker,
    create_context_llm,
    create_embeddings,
    extractions_to_langchain,
    inject_context_sync,
    parsed_to_langchain,
)
from docpipe.ingestion.legacy_executor import LegacyIngestionExecutor
from docpipe.vectorstores.factory import create_vectorstore


class IngestionPipeline:
    """Compatibility API delegating writes to typed vector plugin facets.

    A caller-supplied runtime remains caller-owned and must already be active.
    Legacy SDK callers receive a short-lived runtime whose blocking and plugin
    resources close after each ingestion operation.
    """

    def __init__(
        self,
        config: IngestionConfig,
        *,
        runtime: DocpipeRuntime | None = None,
    ) -> None:
        self._config = config
        self._runtime = runtime
        self._embeddings = self._create_embeddings(config)
        self._chunker = self._create_chunker(config)

    def ingest(
        self,
        parsed: ParsedDocument,
        *,
        extractions: list[ExtractionResult] | None = None,
    ) -> IngestionResult:
        """Synchronously ingest through the async coordinator.

        Raises:
            ConfigurationError: If called from an active event loop. Async callers
                must use :meth:`aingest` to preserve cancellation and cleanup.
            IngestionError: If ingestion cannot complete safely.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.aingest(parsed, extractions=extractions))
        raise ConfigurationError("ingest() cannot run inside an event loop; use aingest()")

    async def aingest(
        self,
        parsed: ParsedDocument,
        *,
        extractions: list[ExtractionResult] | None = None,
    ) -> IngestionResult:
        """Asynchronously ingest while preserving runtime lifecycle ownership."""
        if self._runtime is not None:
            if not self._runtime.is_active:
                raise RuntimeError("caller-owned Docpipe runtime is not active")
            return await self._ingest_with_runtime(self._runtime, parsed, extractions)

        runtime = _build_compatibility_runtime(self._config.max_in_flight)
        async with runtime:
            return await self._ingest_with_runtime(runtime, parsed, extractions)

    async def _ingest_with_runtime(
        self,
        runtime: DocpipeRuntime,
        parsed: ParsedDocument,
        extractions: list[ExtractionResult] | None,
    ) -> IngestionResult:
        if not runtime.settings.plugin_foundation_enabled:
            legacy = LegacyIngestionExecutor(
                self._config,
                embeddings=self._embeddings,
                chunker=self._chunker,
                context_llm_factory=self._create_context_llm,
            )
            return await runtime.blocking_runner.run(legacy.ingest, parsed, extractions)
        contextualizer = None
        if self._config.contextual_injection:
            llm = cast(LegacyLlm, self._create_context_llm(self._config))
            contextualizer = ContextualInjector(
                LangChainContextGenerator(llm, runtime.blocking_runner)
            )
        coordinator = build_ingestion_coordinator(
            self._config,
            runtime=runtime,
            embeddings=self._embeddings,
            chunker=self._chunker,
            contextualizer=contextualizer,
        )
        return await coordinator.ingest(parsed, extractions=extractions)

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        """Preserve legacy similarity-search behavior until retrieval migration."""
        try:
            connection_string = self._config.connection_string
            if connection_string is None:
                raise ConfigurationError("legacy search requires connection_string")
            vectorstore = create_vectorstore(
                embeddings=self._embeddings,
                table_name=self._config.table_name,
                connection_string=connection_string,
                vector_backend=self._vector_backend(),
                turbovec_index_dir=self._turbovec_index_dir(),
                turbovec_bit_width=self._config.turbovec_bit_width,
            )
            results = vectorstore.similarity_search_with_score(
                query,
                k=top_k,
                filter=filters or None,
            )
            return [
                {
                    "content": document.page_content,
                    "metadata": document.metadata,
                    "score": float(score),
                }
                for document, score in results
            ]
        except Exception as exc:
            raise IngestionError("vector search failed") from exc

    def _vector_backend(self) -> str:
        return self._config.vector_backend or "pgvector"

    def _turbovec_index_dir(self) -> str:
        return str(Path(self._config.turbovec_index_dir or ".docpipe/indices").expanduser())

    @staticmethod
    def _compute_source_hash(source: str) -> str:
        """Preserve the deprecated source-only hashing helper."""
        try:
            with Path(source).open("rb") as stream:
                return hashlib.sha256(stream.read()).hexdigest()
        except OSError:
            return hashlib.sha256(source.encode("utf-8")).hexdigest()

    def _hash_exists(self, source_hash: str) -> bool:
        """Preserve deprecated fail-open lookup for explicit legacy callers."""
        try:
            connection_string = self._config.connection_string
            if connection_string is None:
                return False
            store = create_vectorstore(
                embeddings=self._embeddings,
                table_name=self._config.table_name,
                connection_string=connection_string,
                vector_backend=self._vector_backend(),
                turbovec_index_dir=self._turbovec_index_dir(),
                turbovec_bit_width=self._config.turbovec_bit_width,
            )
            return bool(store.similarity_search("", k=1, filter={"source_hash": source_hash}))
        except Exception:  # noqa: BLE001 -- retained only as explicit legacy behavior.
            return False

    @staticmethod
    def _parsed_to_lc_docs(parsed: ParsedDocument) -> list[object]:
        """Preserve the deprecated LangChain conversion helper."""
        return parsed_to_langchain(parsed)

    @staticmethod
    def _extractions_to_lc_docs(
        extractions: list[ExtractionResult],
        source: str,
    ) -> list[object]:
        """Preserve the deprecated LangChain extraction conversion helper."""
        return extractions_to_langchain(extractions, source)

    @staticmethod
    def _create_embeddings(config: IngestionConfig) -> object:
        """Preserve the patchable legacy embedding construction seam."""
        return create_embeddings(config)

    @staticmethod
    def _create_splitter(config: IngestionConfig) -> object:
        """Return the legacy recursive splitter for compatibility."""
        from docpipe.chunkers.recursive_chunker import RecursiveChunker

        return RecursiveChunker._build_splitter(config)

    @staticmethod
    def _create_chunker(config: IngestionConfig) -> object:
        """Preserve the patchable legacy chunker construction seam."""
        return create_chunker(config)

    @staticmethod
    def _create_context_llm(config: IngestionConfig) -> object:
        """Preserve the patchable legacy contextual-model construction seam."""
        return create_context_llm(config)

    @staticmethod
    def _inject_context(
        chunks: list[object],
        full_text: str,
        llm: object,
    ) -> list[object]:
        """Preserve deprecated synchronous contextual injection."""
        return inject_context_sync(chunks, full_text, cast(LegacyLlm, llm))


def _build_compatibility_runtime(max_concurrency: int) -> DocpipeRuntime:
    """Build an explicit runtime without reading process-global settings."""
    settings = DocpipeSettings.model_construct(
        max_concurrency=max_concurrency,
        disabled_plugins=None,
    )
    return build_runtime(settings)
