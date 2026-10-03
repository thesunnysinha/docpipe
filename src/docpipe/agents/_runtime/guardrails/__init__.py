"""Framework-neutral guardrails shared by every generated backend."""

from docpipe.agents._runtime.guardrails.base import BaseGuardrail
from docpipe.agents._runtime.guardrails.loop_guard import DUPLICATE_PREFIX, FEEDBACK_FLAG, LoopGuardrail, current_turn
from docpipe.agents._runtime.guardrails.pii import PIIGuardrail
from docpipe.agents._runtime.guardrails.security import SecurityGuardrail

__all__ = [
    "BaseGuardrail",
    "DUPLICATE_PREFIX",
    "FEEDBACK_FLAG",
    "LoopGuardrail",
    "PIIGuardrail",
    "SecurityGuardrail",
    "current_turn",
]
