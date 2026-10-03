"""Privacy-conscious structured lifecycle logs for LangChain tool invocations.

Events:
- ``agent.tool.started``: tool name, run ID, and argument field names
- ``agent.tool.completed``: the start fields, duration, and output character count
- ``agent.tool.failed``: the start fields, duration, and exception type

Argument values, tool results, and exception messages are deliberately omitted because
they may contain business data or personal information.
"""

from __future__ import annotations

from threading import Lock
from time import monotonic
from typing import Any, Callable, Dict, Mapping, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from docpipe.agents._runtime.telemetry import get_logger

logger = get_logger(__name__)


class ToolCallLoggingHandler(BaseCallbackHandler):
    """Emit one structured log for each tool start, completion, and failure."""

    def __init__(self, on_progress: Optional[Callable[[str, str, str], None]] = None) -> None:
        self._lock = Lock()
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._on_progress = on_progress

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        del input_str, parent_run_id, tags, metadata
        tool_name = str(serialized.get("name") or kwargs.get("name") or "unknown")
        tool_inputs = inputs if isinstance(inputs, Mapping) else kwargs.get("inputs")
        argument_names = sorted(str(key) for key in tool_inputs) if isinstance(tool_inputs, Mapping) else []
        key = str(run_id)
        started_at = monotonic()
        with self._lock:
            self._runs[key] = {
                "tool_name": tool_name,
                "argument_names": argument_names,
                "started_at": started_at,
            }
        logger.info(
            "agent.tool.started",
            tool_name=tool_name,
            tool_run_id=key,
            argument_names=argument_names,
        )
        self._publish(tool_name, "started", key)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        del parent_run_id, tags
        run = self._finish_run(run_id)
        tool_name = run.get("tool_name") or kwargs.get("name") or "unknown"
        logger.info(
            "agent.tool.completed",
            tool_name=tool_name,
            tool_run_id=str(run_id),
            argument_names=run.get("argument_names", []),
            duration_ms=self._duration_ms(run),
            output_chars=len(str(output)),
        )
        self._publish(str(tool_name), "completed", str(run_id))

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        del parent_run_id, tags
        run = self._finish_run(run_id)
        logger.warning(
            "agent.tool.failed",
            tool_name=run.get("tool_name") or kwargs.get("name") or "unknown",
            tool_run_id=str(run_id),
            argument_names=run.get("argument_names", []),
            duration_ms=self._duration_ms(run),
            error_type=type(error).__name__,
        )
        self._publish(str(run.get("tool_name") or kwargs.get("name") or "unknown"), "failed", str(run_id))

    def _publish(self, tool_name: str, status: str, run_id: str) -> None:
        if self._on_progress is not None:
            self._on_progress(tool_name, status, run_id)

    def _finish_run(self, run_id: UUID) -> Dict[str, Any]:
        with self._lock:
            return self._runs.pop(str(run_id), {})

    @staticmethod
    def _duration_ms(run: Dict[str, Any]) -> Optional[float]:
        started_at = run.get("started_at")
        if started_at is None:
            return None
        return round((monotonic() - started_at) * 1000, 2)
