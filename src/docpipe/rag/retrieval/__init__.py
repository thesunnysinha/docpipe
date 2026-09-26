"""Vendor-neutral retrieval strategies for RAG pipelines."""

from docpipe.rag.retrieval.base import RetrievalResult, RetrievalStrategy, VectorSearch
from docpipe.rag.retrieval.registry import StrategyRegistry

__all__ = ["RetrievalResult", "RetrievalStrategy", "StrategyRegistry", "VectorSearch"]
