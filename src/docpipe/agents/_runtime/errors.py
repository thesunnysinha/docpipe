from __future__ import annotations
from typing import Any, Dict, Optional


class AgentServiceError(Exception):
    http_status: int = 500

    def __init__(self, message: str, error_code: str = "INTERNAL_AGENT_ERROR", details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class GuardrailViolationError(AgentServiceError):
    http_status = 400

    def __init__(self, message: str, violation_type: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message=message, error_code=f"GUARDRAIL_{violation_type.upper()}", details=details)
        self.violation_type = violation_type


class PromptInjectionError(GuardrailViolationError):
    def __init__(self, message: str, pattern: str) -> None:
        super().__init__(message=message, violation_type="PROMPT_INJECTION", details={"matched_pattern": pattern})


class TokenCeilingExceededError(GuardrailViolationError):
    def __init__(self, current_len: int, max_len: int) -> None:
        super().__init__(
            message=f"Input length ({current_len} chars) exceeds maximum ({max_len} chars).",
            violation_type="TOKEN_CEILING_EXCEEDED",
            details={"current_length": current_len, "max_length": max_len},
        )


class OutputHallucinationError(GuardrailViolationError):
    http_status = 422

    def __init__(self, hallucinated_values: list[str]) -> None:
        super().__init__(
            message="Response contained ungrounded numeric values not derived from tool results.",
            violation_type="UNGROUNDED_OUTPUT_HALLUCINATION",
            details={"hallucinated_values": hallucinated_values},
        )


class LoopBreakerError(GuardrailViolationError):
    http_status = 422

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message=f"Agent loop detected: {reason}", violation_type="REPETITIVE_EXECUTION_LOOP", details=details)


class ToolExecutionError(AgentServiceError):
    http_status = 422

    def __init__(self, tool_name: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message=f"Tool '{tool_name}' failed: {reason}", error_code="TOOL_EXECUTION_FAILURE", details=details)
        self.tool_name = tool_name


class GraphUninitializedError(AgentServiceError):
    http_status = 503

    def __init__(self) -> None:
        super().__init__(message="The LangGraph agent is uninitialized.", error_code="GRAPH_NOT_READY")


class ProviderModelError(AgentServiceError):
    http_status = 502

    def __init__(self, provider: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message=f"Provider '{provider}' error: {reason}", error_code="PROVIDER_API_ERROR", details=details)
        self.provider = provider


class ApprovalPendingError(AgentServiceError):
    http_status = 409

    def __init__(self, session_id: str) -> None:
        super().__init__(
            message=f"Session '{session_id}' is waiting for human approval. Resolve it before sending new queries.",
            error_code="APPROVAL_PENDING",
            details={"session_id": session_id},
        )


class NoPendingApprovalError(AgentServiceError):
    http_status = 409

    def __init__(self, session_id: str) -> None:
        super().__init__(
            message=f"Session '{session_id}' has no pending approval.",
            error_code="NO_PENDING_APPROVAL",
            details={"session_id": session_id},
        )


class ChatNotFoundError(AgentServiceError):
    http_status = 404

    def __init__(self, session_id: str) -> None:
        super().__init__(
            message=f"Chat '{session_id}' was not found.",
            error_code="CHAT_NOT_FOUND",
            details={"session_id": session_id},
        )
