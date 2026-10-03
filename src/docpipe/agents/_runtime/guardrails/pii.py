from __future__ import annotations
import re
from docpipe.agents._runtime.telemetry import get_logger
from docpipe.agents._runtime.guardrails.base import BaseGuardrail

logger = get_logger(__name__)


class PIIGuardrail(BaseGuardrail):
    SSN_PATTERN: re.Pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    CREDIT_CARD_PATTERN: re.Pattern = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
    EMAIL_PATTERN: re.Pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b")

    def evaluate(self, target: str) -> str:
        sanitized = self.SSN_PATTERN.sub("[REDACTED_SSN]", target)
        sanitized = self.CREDIT_CARD_PATTERN.sub("[REDACTED_CREDIT_CARD]", sanitized)
        sanitized = self.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", sanitized)
        if sanitized != target:
            logger.info("guardrail.pii.redacted")
        return sanitized
