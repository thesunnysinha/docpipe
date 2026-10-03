from __future__ import annotations
import re
from typing import List, Optional, Tuple
from docpipe.agents._runtime.telemetry import get_logger
from docpipe.agents._runtime.errors import GuardrailViolationError, PromptInjectionError, TokenCeilingExceededError
from docpipe.agents._runtime.guardrails.base import BaseGuardrail

logger = get_logger(__name__)


class SecurityGuardrail(BaseGuardrail):
    INJECTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE), "IGNORE_INSTRUCTIONS"),
        (re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE), "SYSTEM_ROLE_SIMULATION"),
        (re.compile(r"reveal\s+(the\s+)?(system\s+prompt|developer\s+instructions)", re.IGNORECASE), "PROMPT_EXTRACTION"),
        (re.compile(r"bypass\s+(guardrails|safety\s+filters|policies)", re.IGNORECASE), "SAFETY_BYPASS"),
        (re.compile(r"you\s+are\s+now\s+in\s+DAN\s+mode", re.IGNORECASE), "JAILBREAK_ATTEMPT"),
    ]
    MIN_CHARS: int = 2
    MAX_CHARS: int = 4000
    # Subclasses can override the three limits above (``MAX_CHARS`` may be a property, so it can follow live
    # configuration), the pattern list, and this message for the too-short case.
    TOO_SHORT_MESSAGE: Optional[str] = None

    def evaluate(self, target: str) -> str:
        cleaned = target.strip()
        if len(cleaned) < self.MIN_CHARS:
            raise GuardrailViolationError(
                message=self.TOO_SHORT_MESSAGE or f"Input is too short (minimum {self.MIN_CHARS} characters).",
                violation_type="INPUT_TOO_SHORT",
                details={"current_length": len(cleaned), "min_length": self.MIN_CHARS},
            )
        if len(cleaned) > self.MAX_CHARS:
            raise TokenCeilingExceededError(current_len=len(cleaned), max_len=self.MAX_CHARS)
        for pattern, label in self.INJECTION_PATTERNS:
            if pattern.search(cleaned):
                logger.warning("guardrail.security.injection_blocked", pattern=label)
                raise PromptInjectionError(message=f"Query matched forbidden override pattern: '{label}'.", pattern=label)
        return cleaned
