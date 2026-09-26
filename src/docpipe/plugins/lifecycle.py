"""Explicit process, request, and operation plugin lifecycles."""

from __future__ import annotations

import inspect
import logging
from asyncio import Lock
from collections.abc import Awaitable, Callable
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
)
from enum import Enum
from types import TracebackType
from typing import cast

_LOGGER = logging.getLogger(__name__)
ResourceFactory = Callable[[], object | Awaitable[object]]


class PluginScope(str, Enum):
    """Supported ownership scopes for plugin instances."""

    OPERATION = "operation"
    REQUEST = "request"
    PROCESS = "process"


class _ScopeNode:
    """One cache and exit stack in a nested scope tree."""

    def __init__(
        self,
        kind: PluginScope,
        *,
        parent: _ScopeNode | None = None,
        logger: logging.Logger,
    ) -> None:
        self.kind = kind
        self.parent = parent
        self.logger = logger
        self.stack = AsyncExitStack()
        self.instances: dict[str, object] = {}
        self.lock = Lock()
        self.closed = False

    def target(self, scope: PluginScope) -> _ScopeNode:
        """Find the nearest owning node for a requested scope."""
        current: _ScopeNode | None = self
        while current is not None and current.kind is not scope:
            current = current.parent
        if current is None:
            raise ValueError(f"{scope.value} scope is not active")
        return current

    async def acquire(self, key: str, factory: ResourceFactory) -> object:
        """Construct and enter a resource once within this node."""
        if self.closed:
            raise RuntimeError(f"{self.kind.value} plugin scope is closed")
        async with self.lock:
            if key in self.instances:
                return self.instances[key]
            candidate = factory()
            if inspect.isawaitable(candidate):
                candidate = await cast(Awaitable[object], candidate)
            instance = await _enter_resource(self.stack, candidate)
            self.instances[key] = instance
            return instance

    async def close(self) -> None:
        """Close all entered resources exactly once in reverse order."""
        if self.closed:
            return
        self.closed = True
        await self.stack.aclose()
        for key in self.instances:
            self.logger.info(
                "plugin.instance.closed",
                extra={
                    "event": "plugin.instance.closed",
                    "scope": self.kind.value,
                    "instance_key": key,
                },
            )
        self.instances.clear()


async def _enter_resource(stack: AsyncExitStack, candidate: object) -> object:
    if hasattr(candidate, "__aenter__") and hasattr(candidate, "__aexit__"):
        async_manager = cast(AbstractAsyncContextManager[object], candidate)
        return await stack.enter_async_context(async_manager)
    if hasattr(candidate, "__enter__") and hasattr(candidate, "__exit__"):
        sync_manager = cast(AbstractContextManager[object], candidate)
        return stack.enter_context(sync_manager)
    return candidate


class PluginScopeHandle:
    """Resource access within one active lifecycle scope."""

    def __init__(self, node: _ScopeNode) -> None:
        self._node = node

    async def acquire(
        self,
        key: str,
        factory: ResourceFactory,
        *,
        scope: PluginScope | None = None,
    ) -> object:
        """Acquire a cached resource owned by this or an ancestor scope."""
        target = self._node.target(scope or self._node.kind)
        return await target.acquire(key, factory)

    def operation_scope(self) -> PluginScopeContext:
        """Create an operation scope nested beneath this request."""
        if self._node.kind is not PluginScope.REQUEST:
            raise ValueError("operation scopes must be nested under request scopes")
        return PluginScopeContext(
            PluginScope.OPERATION,
            parent=self._node,
            logger=self._node.logger,
        )


class PluginScopeContext:
    """Async context manager that owns one non-process scope."""

    def __init__(
        self,
        kind: PluginScope,
        *,
        parent: _ScopeNode,
        logger: logging.Logger,
    ) -> None:
        self._node = _ScopeNode(kind, parent=parent, logger=logger)

    async def __aenter__(self) -> PluginScopeHandle:
        """Expose resource access for the new active scope."""
        return PluginScopeHandle(self._node)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close every resource owned by the scope."""
        await self._node.close()


class PluginRuntime:
    """Process-level lifecycle owner and request-scope factory."""

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self._logger = logger or _LOGGER
        self._process: _ScopeNode | None = None

    async def __aenter__(self) -> PluginRuntime:
        """Start one process lifecycle."""
        if self._process is not None:
            raise RuntimeError("plugin runtime is already active")
        self._process = _ScopeNode(PluginScope.PROCESS, logger=self._logger)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close process-scoped resources."""
        if self._process is not None:
            await self._process.close()

    async def acquire(self, key: str, factory: ResourceFactory) -> object:
        """Acquire one process-scoped resource."""
        return await self._require_process().acquire(key, factory)

    def request_scope(self) -> PluginScopeContext:
        """Create a request scope beneath the active process scope."""
        return PluginScopeContext(
            PluginScope.REQUEST,
            parent=self._require_process(),
            logger=self._logger,
        )

    def _require_process(self) -> _ScopeNode:
        if self._process is None or self._process.closed:
            raise RuntimeError("plugin runtime is not active")
        return self._process
