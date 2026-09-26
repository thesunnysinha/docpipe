"""Lazy provider factories retained for the RAG SDK compatibility surface."""

from __future__ import annotations

import importlib
from typing import Any

from docpipe.core.errors import ConfigurationError
from docpipe.core.types import RAGConfig

EMBEDDING_PROVIDERS: dict[str, tuple[str, str, str, str | None]] = {
    "openai": ("langchain_openai", "OpenAIEmbeddings", "model", "openai_api_key"),
    "google": ("langchain_google_genai", "GoogleGenerativeAIEmbeddings", "model", "google_api_key"),
    "ollama": ("langchain_ollama", "OllamaEmbeddings", "model", None),
    "huggingface": ("langchain_huggingface", "HuggingFaceEmbeddings", "model_name", None),
}

LLM_PROVIDERS: dict[str, tuple[str, str, str | None]] = {
    "openai": ("langchain_openai", "ChatOpenAI", "api_key"),
    "google": ("langchain_google_genai", "ChatGoogleGenerativeAI", "google_api_key"),
    "ollama": ("langchain_ollama", "ChatOllama", None),
    "anthropic": ("langchain_anthropic", "ChatAnthropic", "api_key"),
}


def create_embeddings(config: RAGConfig) -> Any:
    """Construct the requested embedding provider only for a selected query."""
    if config.embedding_provider not in EMBEDDING_PROVIDERS:
        raise ConfigurationError(
            f"Unknown embedding provider: '{config.embedding_provider}'. "
            f"Available: {list(EMBEDDING_PROVIDERS)}"
        )
    module, class_name, model_kwarg, key_kwarg = EMBEDDING_PROVIDERS[config.embedding_provider]
    cls = _load(module, class_name, "Embedding", config.embedding_provider)
    options = {model_kwarg: config.embedding_model}
    if key_kwarg and config.embedding_api_key:
        options[key_kwarg] = config.embedding_api_key
    return cls(**options)


def create_llm(provider: str, model: str, api_key: str | None = None) -> Any:
    """Construct a selected LangChain LLM without importing unused providers."""
    if provider not in LLM_PROVIDERS:
        raise ConfigurationError(
            f"Unknown LLM provider: '{provider}'. Available: {list(LLM_PROVIDERS)}"
        )
    module, class_name, key_kwarg = LLM_PROVIDERS[provider]
    cls = _load(module, class_name, "LLM", provider)
    options = {"model": model}
    if key_kwarg and api_key:
        options[key_kwarg] = api_key
    return cls(**options)


def _load(module: str, class_name: str, kind: str, provider: str) -> Any:
    try:
        return getattr(importlib.import_module(module), class_name)
    except (ImportError, AttributeError) as error:
        raise ConfigurationError(
            f"{kind} provider '{provider}' requires '{module}'. Install {module}"
        ) from error
