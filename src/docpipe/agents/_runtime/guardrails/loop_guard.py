from __future__ import annotations
import hashlib
import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from docpipe.agents._runtime.telemetry import get_logger
from docpipe.agents._runtime.guardrails.base import BaseGuardrail

logger = get_logger(__name__)

DUPLICATE_PREFIX = "Duplicate call suppressed"
FEEDBACK_FLAG = "guardrail_feedback"


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def current_turn(messages: Sequence[BaseMessage]) -> List[BaseMessage]:
    """Messages since the user's latest real question (guardrail feedback does not start a new turn)."""
    for idx in range(len(messages) - 1, -1, -1):
        msg = messages[idx]
        if isinstance(msg, HumanMessage) and not msg.additional_kwargs.get(FEEDBACK_FLAG):
            return list(messages[idx:])
    return list(messages)


class LoopGuardrail(BaseGuardrail):
    """Layered loop defence: step budget, duplicate-call debounce, repeat cap, no-progress window.

    A recursion limit only caps runaway cost; these checks notice that steps are identical
    (same call, same result) and stop the agent with a useful fallback instead.
    """

    MAX_TOTAL_STEPS: int = 8
    MAX_IDENTICAL_TOOL_CALLS: int = 2
    NO_PROGRESS_WINDOW: int = 6
    NO_PROGRESS_REPEATS: int = 3

    def __init__(self, write_tools: Iterable[str] = ()) -> None:
        """``write_tools`` are tools with side effects; a call to one starts a fresh window."""
        self.write_tools = frozenset(write_tools)

    @staticmethod
    def compute_call_signature(tool_name: str, tool_args: Dict[str, Any]) -> str:
        return _digest({"name": tool_name, "args": tool_args})

    def _completed_calls(self, turn: Sequence[BaseMessage]) -> List[Tuple[str, str, str]]:
        """(call_signature, result_signature, result_text) per finished tool call, since the last write."""
        pending: Dict[str, str] = {}
        calls: List[Tuple[str, str, str]] = []
        for msg in turn:
            if isinstance(msg, AIMessage):
                for call in msg.tool_calls:
                    pending[call["id"]] = self.compute_call_signature(call["name"], call["args"])
            elif isinstance(msg, ToolMessage):
                if msg.name in self.write_tools:
                    calls.clear()
                    continue
                sig = pending.get(msg.tool_call_id)
                if sig is not None:
                    text = str(msg.content)
                    calls.append((sig, _digest(" ".join(text.split())), text))
        return calls

    def previous_result(self, tool_name: str, tool_args: Dict[str, Any], turn: Sequence[BaseMessage]) -> Optional[str]:
        sig = self.compute_call_signature(tool_name, tool_args)
        for call_sig, _, text in self._completed_calls(turn):
            if call_sig == sig and not text.startswith(DUPLICATE_PREFIX):
                return text
        return None

    def would_repeat_too_often(self, tool_name: str, tool_args: Dict[str, Any], turn: Sequence[BaseMessage]) -> bool:
        sig = self.compute_call_signature(tool_name, tool_args)
        attempts = sum(1 for call_sig, _, _ in self._completed_calls(turn) if call_sig == sig)
        if attempts >= self.MAX_IDENTICAL_TOOL_CALLS:
            logger.error("guardrail.loop.repeat_limit", tool=tool_name, attempts=attempts)
            return True
        return False

    def no_progress(self, turn: Sequence[BaseMessage]) -> bool:
        window = self._completed_calls(turn)[-self.NO_PROGRESS_WINDOW :]
        for _, result_sig, _ in window:
            if sum(1 for _, other, _ in window if other == result_sig) >= self.NO_PROGRESS_REPEATS:
                logger.error("guardrail.loop.no_progress")
                return True
        return False

    def evaluate(self, target: Any) -> Any:
        return target
