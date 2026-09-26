"""Asynchronous TurboVec facets over a synchronous repository boundary."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Protocol, TypeVar

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    SourceAggregate,
    VectorCapability,
    VectorMatch,
    VectorQuery,
    VectorStoreBinding,
    WriteBatch,
    WriteBatchResult,
)
from docpipe.plugins.errors import PublicIntegrationError, VectorStoreOperationError
from docpipe.vectorstores.turbovec.configuration import TurboVecConfig

_LOGGER = logging.getLogger(__name__)
Result = TypeVar("Result")


class TurboVecRepository(Protocol):
    """Blocking persistence operations used by :class:`TurboVecAdapter`."""

    def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None:
        """Create the collection if absent and reject incompatible dimensions."""
        ...

    def delete_collection(self, collection: CollectionRef) -> None:
        """Remove the collection and its persisted records and snapshot."""
        ...

    def upsert(self, batch: WriteBatch) -> int:
        """Persist a complete batch and return the accepted record count."""
        ...

    def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]:
        """Return ordered matches honoring query filters and result limit."""
        ...

    def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        """Delete exact source matches and return their count."""
        ...

    def aggregate_sources(self, collection: CollectionRef) -> tuple[SourceAggregate, ...]:
        """Return record totals grouped by source identifier."""
        ...

    def health(self) -> bool:
        """Return whether the configured local index root is usable."""
        ...


class TurboVecAdapter:
    """TurboVec implementation of dense reader, writer, admin, and health facets.

    All local operations share one asynchronous lock. The repository also owns a
    thread lock because cancellation cannot stop an already-running blocking call.
    """

    capabilities = frozenset(
        {
            VectorCapability.DENSE_SEARCH,
            VectorCapability.METADATA_FILTER,
            VectorCapability.SOURCE_AGGREGATION,
            VectorCapability.UPSERT,
            VectorCapability.DELETE_BY_SOURCE,
            VectorCapability.COLLECTION_ADMIN,
            VectorCapability.HEALTH,
        }
    )

    def __init__(
        self,
        config: TurboVecConfig,
        repository: TurboVecRepository,
        blocking_runner: BoundedBlockingRunner,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = config
        self._repository = repository
        self._runner = blocking_runner
        self._logger = logger or _LOGGER
        self._operation_lock = asyncio.Lock()

    @property
    def binding(self) -> VectorStoreBinding:
        """Return this adapter's implemented facets and explicit capabilities."""
        return VectorStoreBinding(
            capabilities=self.capabilities,
            reader=self,
            writer=self,
            admin=self,
            health=self,
        )

    async def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None:
        """Ensure a collection exists with compatible dimensions."""
        await self._locked(
            "vectorstore.collection.ensure",
            lambda: self._runner.run(
                self._repository.ensure_collection,
                collection,
                dimensions,
            ),
        )

    async def delete_collection(self, collection: CollectionRef) -> None:
        """Delete a collection and its local snapshot."""
        await self._locked(
            "vectorstore.collection.delete",
            lambda: self._runner.run(self._repository.delete_collection, collection),
        )

    async def upsert(self, batch: WriteBatch) -> WriteBatchResult:
        """Serialize and atomically publish an upsert batch."""
        accepted = await self._locked(
            "vectorstore.upsert",
            lambda: self._runner.run(self._repository.upsert, batch),
        )
        return WriteBatchResult(
            requested=len(batch.records),
            accepted=accepted,
            rejected=len(batch.records) - accepted,
        )

    async def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]:
        """Search the selected dense collection with optional typed filters."""
        return await self._locked(
            "vectorstore.search",
            lambda: self._runner.run(self._repository.search, query),
        )

    async def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        """Delete records matching an exact source identifier."""
        return await self._locked(
            "vectorstore.delete.source",
            lambda: self._runner.run(
                self._repository.delete_by_source,
                collection,
                source_id,
            ),
        )

    async def aggregate_sources(self, collection: CollectionRef) -> tuple[SourceAggregate, ...]:
        """Aggregate record counts by source identifier."""
        return await self._locked(
            "vectorstore.aggregate.sources",
            lambda: self._runner.run(self._repository.aggregate_sources, collection),
        )

    async def health(self) -> bool:
        """Check local filesystem availability without loading an index."""
        return await self._execute(
            "vectorstore.health",
            self._runner.run(self._repository.health),
        )

    async def _locked(
        self,
        event: str,
        operation_factory: Callable[[], Awaitable[Result]],
    ) -> Result:
        async with self._operation_lock:
            return await self._execute(event, operation_factory())

    async def _execute(self, event: str, operation: Awaitable[Result]) -> Result:
        started = monotonic()
        self._logger.info(f"{event}.started", extra={"event": f"{event}.started"})
        try:
            result = await operation
        except PublicIntegrationError:
            raise
        except Exception as exc:
            self._logger.warning(
                f"{event}.failed",
                extra={
                    "event": f"{event}.failed",
                    "error_code": "vectorstore_operation_failed",
                },
            )
            raise VectorStoreOperationError(
                "TurboVec operation failed",
                context={"provider": "turbovec", "operation": event},
            ) from exc
        self._logger.info(
            f"{event}.completed",
            extra={
                "event": f"{event}.completed",
                "duration_ms": round((monotonic() - started) * 1000, 3),
            },
        )
        return result
