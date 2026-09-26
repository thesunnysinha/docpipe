"""Bounded orchestration over chunking, encoding, and vector facets."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager, AsyncExitStack
from time import monotonic
from typing import Protocol

from docpipe.core.errors import IngestionError
from docpipe.core.types import ExtractionResult, IngestionResult, ParsedDocument
from docpipe.embeddings.contracts import EmbeddingEncoder
from docpipe.ingestion.configuration import IncrementalFailureMode, IngestionOptions
from docpipe.ingestion.contextualization import Contextualizer
from docpipe.ingestion.document_builder import IngestionDocument
from docpipe.ingestion.errors import IncompleteIngestionError as IncompleteIngestionError
from docpipe.ingestion.errors import IncrementalStateError
from docpipe.ingestion.incremental import (
    IncrementalDecider,
    parsed_document_fingerprint,
)
from docpipe.plugins.contracts.vectorstore import (
    VectorCollectionAdmin,
    VectorRecord,
    VectorWriter,
    WriteBatch,
)

_LOGGER = logging.getLogger(__name__)
OperationScopeFactory = Callable[[], AbstractAsyncContextManager[object]]


class IngestionDocumentBuilder(Protocol):
    """Build source documents without exposing parser or framework objects."""

    def build(
        self,
        parsed: ParsedDocument,
        extractions: Sequence[ExtractionResult] | None = None,
    ) -> tuple[IngestionDocument, ...]:
        """Return selected source representations in deterministic order."""
        ...


class IngestionChunker(Protocol):
    """Split immutable Docpipe documents into immutable chunks."""

    async def split(
        self,
        documents: tuple[IngestionDocument, ...],
    ) -> tuple[IngestionDocument, ...]:
        """Return chunks in deterministic source order."""
        ...


class IngestionCoordinator:
    """Coordinate one ingestion without vendor imports or global configuration."""

    def __init__(
        self,
        *,
        options: IngestionOptions,
        builder: IngestionDocumentBuilder,
        chunker: IngestionChunker,
        encoder: EmbeddingEncoder,
        writer: VectorWriter,
        admin: VectorCollectionAdmin,
        incremental_decider: IncrementalDecider | None = None,
        contextualizer: Contextualizer | None = None,
        operation_scope_factory: OperationScopeFactory | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._options = options
        self._builder = builder
        self._chunker = chunker
        self._encoder = encoder
        self._writer = writer
        self._admin = admin
        self._incremental_decider = incremental_decider
        self._contextualizer = contextualizer
        self._operation_scope_factory = operation_scope_factory
        self._logger = logger or _LOGGER

    async def ingest(
        self,
        parsed: ParsedDocument,
        *,
        extractions: Sequence[ExtractionResult] | None = None,
    ) -> IngestionResult:
        """Build, chunk, encode, and completely persist one parsed document.

        Raises:
            IncrementalStateError: When fail-closed duplicate lookup is unavailable.
            IncompleteIngestionError: When any write is rejected or uncertain.
            IngestionError: When another ingestion stage fails.
            asyncio.CancelledError: When the caller cancels the operation; acquired
                operation resources are closed before propagation.
        """
        started = monotonic()
        self._logger.info("ingestion.started", extra={"event": "ingestion.started"})
        try:
            async with AsyncExitStack() as stack:
                if self._operation_scope_factory is not None:
                    await stack.enter_async_context(self._operation_scope_factory())
                result = await self._run(parsed, extractions)
        except asyncio.CancelledError:
            self._log_failure("ingestion_cancelled")
            raise
        except IngestionError:
            self._log_failure("ingestion_failed")
            raise
        except Exception as exc:
            self._log_failure("ingestion_failed")
            raise IngestionError("ingestion operation failed") from exc
        self._logger.info(
            "ingestion.write.completed",
            extra={
                "event": "ingestion.write.completed",
                "chunk_count": result.chunks_ingested,
                "duration_ms": round((monotonic() - started) * 1000, 3),
            },
        )
        return result

    async def _run(
        self,
        parsed: ParsedDocument,
        extractions: Sequence[ExtractionResult] | None,
    ) -> IngestionResult:
        documents = self._builder.build(parsed, extractions)
        if not documents:
            return self._result(parsed, chunks=0, created=False)

        if self._options.incremental:
            fingerprint = parsed_document_fingerprint(parsed)
            if await self._should_skip(fingerprint):
                return self._result(parsed, chunks=0, created=False, skipped=1)
            documents = tuple(
                document.with_metadata({"source_hash": fingerprint}) for document in documents
            )

        chunk_started = monotonic()
        chunks = await self._chunker.split(documents)
        if self._options.chunk_metadata:
            chunks = tuple(chunk.with_metadata(self._options.chunk_metadata) for chunk in chunks)
        self._logger.info(
            "ingestion.chunking.completed",
            extra={
                "event": "ingestion.chunking.completed",
                "document_count": len(documents),
                "chunk_count": len(chunks),
                "duration_ms": round((monotonic() - chunk_started) * 1000, 3),
            },
        )
        if not chunks:
            return self._result(parsed, chunks=0, created=False)
        if self._contextualizer is not None:
            chunks = await self._contextualizer.apply(chunks, parsed.text)
        accepted = await self._write_batches(chunks)
        return self._result(parsed, chunks=accepted, created=True)

    async def _should_skip(self, fingerprint: str) -> bool:
        if self._incremental_decider is not None:
            return await self._incremental_decider.should_skip(fingerprint)
        if self._options.incremental_failure_mode is IncrementalFailureMode.LEGACY_BEST_EFFORT:
            self._logger.warning(
                "incremental.lookup.failed_open",
                extra={
                    "event": "incremental.lookup.failed_open",
                    "error_code": "incremental_state_unavailable",
                },
            )
            return False
        raise IncrementalStateError("incremental state lookup is unavailable")

    async def _write_batches(self, chunks: tuple[IngestionDocument, ...]) -> int:
        batches = tuple(
            chunks[offset : offset + self._options.batch_size]
            for offset in range(0, len(chunks), self._options.batch_size)
        )
        first = await self._encode_batch(batches[0])
        dimensions = len(first.records[0].vector)
        await self._admin.ensure_collection(self._options.collection, dimensions)
        accepted = await self._write(first)
        if len(batches) == 1:
            return accepted

        semaphore = asyncio.Semaphore(self._options.max_in_flight)

        async def encode_and_write(batch: tuple[IngestionDocument, ...]) -> int:
            async with semaphore:
                return await self._write(await self._encode_batch(batch))

        tasks = [asyncio.create_task(encode_and_write(batch)) for batch in batches[1:]]
        try:
            accepted += sum(await asyncio.gather(*tasks))
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        return accepted

    async def _encode_batch(
        self,
        documents: tuple[IngestionDocument, ...],
    ) -> WriteBatch:
        started = monotonic()
        vectors = await self._encoder.encode_documents(
            tuple(document.text for document in documents)
        )
        if len(vectors) != len(documents):
            raise IngestionError("embedding count does not match chunk count")
        records = tuple(
            VectorRecord(
                record_id=document.record_id,
                text=document.text,
                vector=vector,
                metadata=document.metadata,
                source_id=document.source_id,
            )
            for document, vector in zip(documents, vectors, strict=True)
        )
        self._logger.info(
            "ingestion.embedding.completed",
            extra={
                "event": "ingestion.embedding.completed",
                "chunk_count": len(records),
                "duration_ms": round((monotonic() - started) * 1000, 3),
            },
        )
        return WriteBatch(self._options.collection, records)

    async def _write(self, batch: WriteBatch) -> int:
        result = await self._writer.upsert(batch)
        if result.rejected or result.uncertain or result.accepted != result.requested:
            self._logger.warning(
                "ingestion.partial",
                extra={
                    "event": "ingestion.partial",
                    "requested": result.requested,
                    "accepted": result.accepted,
                    "rejected": result.rejected,
                    "uncertain": result.uncertain,
                },
            )
            raise IncompleteIngestionError(result)
        return result.accepted

    def _result(
        self,
        parsed: ParsedDocument,
        *,
        chunks: int,
        created: bool,
        skipped: int = 0,
    ) -> IngestionResult:
        return IngestionResult(
            source=parsed.source,
            chunks_ingested=chunks,
            skipped=skipped,
            table_name=self._options.collection.name,
            table_created=created,
        )

    def _log_failure(self, error_code: str) -> None:
        self._logger.warning(
            "ingestion.failed",
            extra={"event": "ingestion.failed", "error_code": error_code},
        )
