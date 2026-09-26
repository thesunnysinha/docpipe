"""Small schemas and validators shared across workflows."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


def validate_table_name(v: str) -> str:
    """Validate that a string is a safe PostgreSQL identifier."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v):
        raise ValueError(
            "table_name must be a valid PostgreSQL identifier (letters, digits, underscores only)"
        )
    return v


class TokenUsage(BaseModel):
    """Token counts reported by an LLM provider for one operation.

    Providers may omit individual counts, so every value is optional. ``total_tokens``
    is kept as reported rather than inferred from input and output counts.
    """

    input_tokens: int | None = Field(
        default=None, description="Prompt/input tokens reported by the provider."
    )
    output_tokens: int | None = Field(
        default=None, description="Completion/output tokens reported by the provider."
    )
    total_tokens: int | None = Field(
        default=None, description="Total tokens reported by the provider, when available."
    )
