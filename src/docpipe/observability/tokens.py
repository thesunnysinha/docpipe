"""Extract LLM token usage from LangChain responses and callbacks."""

from __future__ import annotations

from typing import Any

from docpipe.core.types import TokenUsage

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:

    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Fallback when langchain-core is not installed."""


def extract_usage_from_langchain_response(response: Any) -> TokenUsage | None:
    """Read usage_metadata from an AIMessage or LLMResult."""
    usage_meta = getattr(response, "usage_metadata", None)
    if isinstance(usage_meta, dict) and usage_meta:
        return _usage_from_metadata(usage_meta)

    response_metadata = getattr(response, "response_metadata", None) or {}
    token_usage = response_metadata.get("token_usage") or response_metadata.get("usage")
    if isinstance(token_usage, dict):
        return _usage_from_metadata(token_usage)
    return None


def _usage_from_metadata(meta: dict[str, Any]) -> TokenUsage | None:
    input_tokens = meta.get("input_tokens") or meta.get("prompt_tokens")
    output_tokens = meta.get("output_tokens") or meta.get("completion_tokens")
    total_tokens = meta.get("total_tokens")
    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None
    inp = int(input_tokens) if input_tokens is not None else None
    out = int(output_tokens) if output_tokens is not None else None
    total = int(total_tokens) if total_tokens is not None else None
    if total is None and inp is not None and out is not None:
        total = inp + out
    return TokenUsage(input_tokens=inp, output_tokens=out, total_tokens=total)


def merge_usage(*usages: TokenUsage | None) -> TokenUsage | None:
    """Sum token counts across multiple usage records."""
    inp = out = total = 0
    has_any = False
    for usage in usages:
        if usage is None:
            continue
        has_any = True
        if usage.input_tokens is not None:
            inp += usage.input_tokens
        if usage.output_tokens is not None:
            out += usage.output_tokens
        if usage.total_tokens is not None:
            total += usage.total_tokens
    if not has_any:
        return None
    computed_total = total or (inp + out if inp or out else None)
    return TokenUsage(
        input_tokens=inp or None,
        output_tokens=out or None,
        total_tokens=computed_total or None,
    )


class UsageCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that aggregates token usage across calls."""

    def __init__(self) -> None:
        super().__init__()
        self._usages: list[TokenUsage] = []

    @property
    def usage(self) -> TokenUsage | None:
        return merge_usage(*self._usages)

    def reset(self) -> None:
        self._usages.clear()

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        del kwargs
        llm_output = getattr(response, "llm_output", None) or {}
        token_usage = llm_output.get("token_usage")
        if isinstance(token_usage, dict):
            parsed = _usage_from_metadata(token_usage)
            if parsed:
                self._usages.append(parsed)
                return
        generations = getattr(response, "generations", None) or []
        for gen_list in generations:
            for gen in gen_list:
                message = getattr(gen, "message", None)
                if message is not None:
                    parsed = extract_usage_from_langchain_response(message)
                    if parsed:
                        self._usages.append(parsed)
