"""One-release rollback path for the pre-plugin vector ingestion API."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import cast

from docpipe.core.errors import ConfigurationError, IngestionError
from docpipe.core.types import ExtractionResult, IngestionConfig, IngestionResult, ParsedDocument
from docpipe.ingestion.legacy import (
    LegacyChunker,
    LegacyDocument,
    LegacyLlm,
    extractions_to_langchain,
    inject_context_sync,
    parsed_to_langchain,
)
from docpipe.vectorstores.factory import create_vectorstore, ingest_documents

_LOGGER = logging.getLogger(__name__)


class LegacyIngestionExecutor:
    """Run the prior LangChain write path inside a bounded worker thread.

    This path accepts only legacy pgvector/TurboVec settings. It is retained
    temporarily for staged-deployment rollback; new providers require the
    plugin foundation.
    """

    def __init__(
        self,
        config: IngestionConfig,
        *,
        embeddings: object,
        chunker: object,
        context_llm_factory: Callable[[IngestionConfig], object],
    ) -> None:
        self._config = config
        self._embeddings = embeddings
        self._chunker = cast(LegacyChunker, chunker)
        self._context_llm_factory = context_llm_factory

    def ingest(
        self,
        parsed: ParsedDocument,
        extractions: list[ExtractionResult] | None = None,
    ) -> IngestionResult:
        """Convert, chunk, and write through the deprecated vector facade."""
        config = self._config
        if config.vector_store is not None:
            raise ConfigurationError("vector_store requires the plugin foundation")
        if config.connection_string is None:
            raise ConfigurationError("legacy ingestion requires connection_string")
        documents = self._documents(parsed, extractions)
        if not documents:
            return self._result(parsed, chunks=0, table_created=False)
        if config.incremental:
            fingerprint = _source_fingerprint(parsed.source)
            if self._already_ingested(fingerprint):
                _LOGGER.info(
                    "ingestion.legacy.skipped", extra={"event": "ingestion.legacy.skipped"}
                )
                return self._result(parsed, chunks=0, table_created=False, skipped=1)
            for document in documents:
                cast(LegacyDocument, document).metadata["source_hash"] = fingerprint

        chunks = self._chunker.split_documents(documents)
        if config.chunk_metadata:
            for value in chunks:
                cast(LegacyDocument, value).metadata.update(config.chunk_metadata)
        if config.contextual_injection:
            llm = cast(LegacyLlm, self._context_llm_factory(config))
            chunks = inject_context_sync(chunks, parsed.text, llm)
        try:
            ingest_documents(
                documents=chunks,
                embeddings=self._embeddings,
                table_name=config.table_name,
                connection_string=config.connection_string,
                vector_backend=config.vector_backend or "pgvector",
                turbovec_index_dir=config.turbovec_index_dir or ".docpipe/indices",
                turbovec_bit_width=config.turbovec_bit_width,
            )
        except ConfigurationError:
            raise
        except Exception as error:
            raise IngestionError("legacy vector ingestion failed") from error
        _LOGGER.info(
            "ingestion.legacy.completed",
            extra={"event": "ingestion.legacy.completed", "chunk_count": len(chunks)},
        )
        return self._result(parsed, chunks=len(chunks), table_created=True)

    def _documents(
        self,
        parsed: ParsedDocument,
        extractions: list[ExtractionResult] | None,
    ) -> list[object]:
        documents: list[object] = []
        if self._config.ingest_mode in ("chunks", "both"):
            documents.extend(parsed_to_langchain(parsed))
        if self._config.ingest_mode in ("extractions", "both") and extractions:
            documents.extend(extractions_to_langchain(extractions, parsed.source))
        return documents

    def _already_ingested(self, fingerprint: str) -> bool:
        config = self._config
        connection_string = config.connection_string
        if connection_string is None:
            raise ConfigurationError("legacy ingestion requires connection_string")
        try:
            store = create_vectorstore(
                embeddings=self._embeddings,
                table_name=config.table_name,
                connection_string=connection_string,
                vector_backend=config.vector_backend or "pgvector",
                turbovec_index_dir=config.turbovec_index_dir or ".docpipe/indices",
                turbovec_bit_width=config.turbovec_bit_width,
            )
            return bool(store.similarity_search("", k=1, filter={"source_hash": fingerprint}))
        except Exception as error:
            if config.incremental_failure_mode == "legacy_best_effort":
                _LOGGER.warning(
                    "ingestion.legacy.incremental_failed_open",
                    extra={"event": "ingestion.legacy.incremental_failed_open"},
                )
                return False
            raise IngestionError("legacy incremental state lookup failed") from error

    def _result(
        self,
        parsed: ParsedDocument,
        *,
        chunks: int,
        table_created: bool,
        skipped: int = 0,
    ) -> IngestionResult:
        return IngestionResult(
            source=parsed.source,
            chunks_ingested=chunks,
            skipped=skipped,
            table_name=self._config.table_name,
            table_created=table_created,
        )


def _source_fingerprint(source: str) -> str:
    """Hash source bytes when present, otherwise its stable identifier."""
    digest = hashlib.sha256()
    try:
        with Path(source).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        return hashlib.sha256(source.encode("utf-8")).hexdigest()
    return digest.hexdigest()
