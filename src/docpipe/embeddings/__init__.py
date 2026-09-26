"""Public embedding ports and boundary adapters."""

from docpipe.embeddings.contracts import EmbeddingEncoder
from docpipe.embeddings.langchain_adapter import LangChainEmbeddingAdapter

__all__ = ["EmbeddingEncoder", "LangChainEmbeddingAdapter"]
