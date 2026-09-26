"""Asynchronous pgvector facets over a synchronous repository boundary."""

from __future__ import annotations

import logging
from collections.abc import Awaitable
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
from docpipe.plugins.errors import (
    PublicIntegrationError,
    VectorStoreConnectionError,
    VectorStoreOperationError,
)
from docpipe.vectorstores.pgvector.configuration import PgVectorConfig

_LOGGER = logging.getLogger(__name__)
Result = TypeVar("Result")


class PgVectorRepository(Protocol):
    """Blocking persistence operations used by :class:`PgVectorAdapter`."""

    def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None: ...

    def delete_collection(self, collection: CollectionRef) -> None: ...

    def upsert(self, batch: WriteBatch) -> int: ...

    def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]: ...

    def delete_by_source(self, collection: CollectionRef, source_id: str) -> int: ...

    def aggregate_sources(self, collection: CollectionRef) -> tuple[SourceAggregate, ...]: ...

    def health(self) -> bool: ...


class PgVectorAdapter:
    """Pgvector implementation of reader, writer, admin, and health facets."""

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
        config: PgVectorConfig,
        repository: PgVectorRepository,
        blocking_runner: BoundedBlockingRunner,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = config
        self._repository = repository
        self._runner = blocking_runner
        self._logger = logger or _LOGGER

    @property
    def binding(self) -> VectorStoreBinding:
        """Return this adapter's typed facets and advertised capabilities."""
        return VectorStoreBinding(
            capabilities=self.capabilities,
            reader=self,
            writer=self,
            admin=self,
            health=self,
        )

    async def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None:
        """Ensure a collection exists with the requested dimensions."""
        await self._execute(
            "vectorstore.collection.ensure",
            self._runner.run(self._repository.ensure_collection, collection, dimensions),
        )

    async def delete_collection(self, collection: CollectionRef) -> None:
        """Delete a collection and all of its records."""
        await self._execute(
            "vectorstore.collection.delete",
            self._runner.run(self._repository.delete_collection, collection),
        )

    async def upsert(self, batch: WriteBatch) -> WriteBatchResult:
        """Upsert a deterministic batch and return complete accounting."""
        accepted = await self._execute(
            "vectorstore.upsert",
            self._runner.run(self._repository.upsert, batch),
        )
        return WriteBatchResult(
            requested=len(batch.records),
            accepted=accepted,
            rejected=len(batch.records) - accepted,
        )

    async def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]:
        """Search dense vectors with optional typed metadata filtering."""
        return await self._execute(
            "vectorstore.search",
            self._runner.run(self._repository.search, query),
        )

    async def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        """Delete records matching an exact normalized source identifier."""
        return await self._execute(
            "vectorstore.delete.source",
            self._runner.run(self._repository.delete_by_source, collection, source_id),
        )

    async def aggregate_sources(self, collection: CollectionRef) -> tuple[SourceAggregate, ...]:
        """Aggregate record counts by source identifier."""
        return await self._execute(
            "vectorstore.aggregate.sources",
            self._runner.run(self._repository.aggregate_sources, collection),
        )

    async def health(self) -> bool:
        """Check database connectivity without exposing connection details."""
        return await self._execute(
            "vectorstore.health",
            self._runner.run(self._repository.health),
        )

    async def _execute(self, event: str, operation: Awaitable[Result]) -> Result:
        self._logger.info(f"{event}.started", extra={"event": f"{event}.started"})
        try:
            result = await operation
        except PublicIntegrationError:
            raise
        except (ConnectionError, OSError) as exc:
            self._logger.warning(
                f"{event}.failed",
                extra={"event": f"{event}.failed", "error_code": "vectorstore_connection_failed"},
            )
            raise VectorStoreConnectionError(
                "pgvector connection is unavailable",
                context={"provider": "pgvector", "operation": event},
            ) from exc
        except Exception as exc:
            self._logger.warning(
                f"{event}.failed",
                extra={"event": f"{event}.failed", "error_code": "vectorstore_operation_failed"},
            )
            raise VectorStoreOperationError(
                "pgvector operation failed",
                context={"provider": "pgvector", "operation": event},
            ) from exc
        self._logger.info(f"{event}.completed", extra={"event": f"{event}.completed"})
        return result
