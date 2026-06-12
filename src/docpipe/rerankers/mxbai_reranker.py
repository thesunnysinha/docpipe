"""mixedbread mxbai cross-encoder reranker."""

from __future__ import annotations

from typing import Any

from docpipe.rerankers.bge_reranker import BGEReranker


class MxbaiReranker(BGEReranker):
    """Same CrossEncoder stack as BGE with mixedbread default model."""

    name = "mxbai"
    license = "Apache-2.0"

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        super().__init__(model=model or "mixedbread-ai/mxbai-rerank-large-v2", **kwargs)
