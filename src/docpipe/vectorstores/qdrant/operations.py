"""Safe Qdrant operation execution and structured lifecycle events."""

from __future__ import annotations

import logging
from collections.abc import Awaitable
from typing import TypeVar

from docpipe.plugins.errors import PublicIntegrationError, VectorStoreOperationError

_LOGGER = logging.getLogger(__name__)
Result = TypeVar("Result")


class QdrantOperations:
    """Translate vendor failures without exposing endpoint or credential text."""

    async def execute(self, event: str, operation: Awaitable[Result]) -> Result:
        """Await one SDK operation and emit safe start/completion/failure events."""
        _LOGGER.info(f"{event}.started", extra={"event": f"{event}.started", "plugin": "qdrant"})
        try:
            result = await operation
        except PublicIntegrationError:
            raise
        except Exception as error:
            _LOGGER.warning(
                f"{event}.failed",
                extra={
                    "event": f"{event}.failed",
                    "plugin": "qdrant",
                    "error_type": type(error).__name__,
                },
            )
            raise VectorStoreOperationError(
                "Qdrant operation failed",
                context={"provider": "qdrant", "operation": event},
            ) from error
        _LOGGER.info(
            f"{event}.completed", extra={"event": f"{event}.completed", "plugin": "qdrant"}
        )
        return result
