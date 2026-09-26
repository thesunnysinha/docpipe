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
    """LLM token usage from provider responses."""

    input_tokens: int | None = Field(default=None)
    output_tokens: int | None = Field(default=None)
    total_tokens: int | None = Field(default=None)
