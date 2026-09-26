"""Immutable context propagated through one Docpipe operation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType

from docpipe.core.errors import OperationDeadlineExceededError as OperationDeadlineExceededError


@dataclass(frozen=True, slots=True)
class OperationContext:
    """Safe request metadata and optional deadline for application operations."""

    request_id: str
    trace_context: Mapping[str, str] = field(default_factory=dict)
    tenant_id: str | None = None
    deadline: datetime | None = None
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        """Validate identifiers and detach metadata from caller-owned mappings."""
        if not self.request_id.strip():
            raise ValueError("request_id must not be empty")
        if self.tenant_id is not None and not self.tenant_id.strip():
            raise ValueError("tenant_id must not be empty")
        if self.deadline is not None and self.deadline.utcoffset() is None:
            raise ValueError("deadline must be timezone-aware")
        object.__setattr__(self, "trace_context", MappingProxyType(dict(self.trace_context)))

    def remaining_seconds(self, *, now: datetime | None = None) -> float | None:
        """Return remaining deadline time, or ``None`` when unbounded."""
        if self.deadline is None:
            return None
        current = now or datetime.now(timezone.utc)
        return max(0.0, (self.deadline - current).total_seconds())

    def ensure_active(self, *, now: datetime | None = None) -> None:
        """Raise a stable error when the deadline has expired."""
        remaining = self.remaining_seconds(now=now)
        if remaining is not None and remaining <= 0:
            raise OperationDeadlineExceededError(
                "operation deadline exceeded",
                context={"request_id": self.request_id},
            )
