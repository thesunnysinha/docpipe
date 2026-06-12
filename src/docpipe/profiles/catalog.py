"""Install profiles and plugin tier metadata."""

from __future__ import annotations

from typing import Any, Literal

InstallProfile = Literal["slim", "balanced", "quality", "agents", "eval", "gpu", "custom"]

RuntimePreset = Literal["fast", "balanced", "quality", "agents"]

# Maps plugin name → recommended tier for discovery UI
PARSER_TIERS: dict[str, str] = {
    "markitdown": "fast",
    "pymupdf": "fast",
    "docling": "balanced",
    "unstructured": "balanced",
    "glm-ocr": "quality",
    "mineru": "quality",
    "paddleocr": "quality",
}

CHUNKER_TIERS: dict[str, str] = {
    "recursive": "fast",
    "semchunk": "balanced",
    "chonkie-semantic": "quality",
    "chonkie-late": "quality",
}

RERANKER_TIERS: dict[str, str] = {
    "none": "fast",
    "flashrank": "fast",
    "cohere": "balanced",
    "bge": "quality",
    "mxbai": "quality",
}

INSTALL_PROFILES: dict[str, dict[str, Any]] = {
    "slim": {
        "description": "Lightweight API: MarkItDown, fast chunking, flashrank rerank.",
        "pip_extra": "profile-slim",
        "docker_tag": "slim",
        "recommended_for": ["sidecars", "high-churn", "office-html"],
    },
    "balanced": {
        "description": "Default production: Docling, semchunk, hybrid RAG, pgvector.",
        "pip_extra": "profile-balanced",
        "docker_tag": "balanced",
        "recommended_for": ["kubernetes", "multi-tenant", "general-rag"],
    },
    "quality": {
        "description": "Higher accuracy: GLM-OCR, chonkie, BGE reranker.",
        "pip_extra": "profile-quality",
        "docker_tag": "quality",
        "recommended_for": ["scanned-pdfs", "complex-layouts"],
    },
    "agents": {
        "description": "Balanced stack plus AutoGen agentic RAG.",
        "pip_extra": "profile-agents",
        "docker_tag": "agents",
        "recommended_for": ["tool-using-assistants", "jingo", "andocs"],
    },
    "eval": {
        "description": "Balanced stack plus RAGAS evaluation metrics.",
        "pip_extra": "profile-eval",
        "docker_tag": "eval",
        "recommended_for": ["rag-benchmarking", "ci-eval"],
    },
    "gpu": {
        "description": "GPU-oriented parsers (MinerU, PaddleOCR) on quality base.",
        "pip_extra": "profile-gpu",
        "docker_tag": "gpu",
        "recommended_for": ["gpu-nodes", "heavy-ocr"],
    },
}

RUNTIME_PRESETS: dict[str, dict[str, Any]] = {
    "fast": {
        "description": "Low latency: auto/fast parsers, recursive chunks, no rerank.",
        "parser": "auto",
        "tier": "fast",
        "chunker": "recursive",
        "reranker": "none",
        "strategy": "naive",
    },
    "balanced": {
        "description": "Default quality/speed: balanced parsers, semchunk, flashrank.",
        "parser": "auto",
        "tier": "balanced",
        "chunker": "semchunk",
        "reranker": "flashrank",
        "strategy": "naive",
    },
    "quality": {
        "description": "Best retrieval: quality parsers, semantic chunks, BGE rerank.",
        "parser": "auto",
        "tier": "quality",
        "chunker": "chonkie-semantic",
        "reranker": "bge",
        "strategy": "hybrid",
    },
    "agents": {
        "description": "Agentic RAG with document search tools.",
        "parser": "auto",
        "tier": "balanced",
        "chunker": "semchunk",
        "reranker": "flashrank",
        "strategy": "naive",
        "agent_backend": "autogen",
        "enable_parse_tool": True,
    },
}

# Max POST requests per minute per client + preset (quality tier is lowest).
PRESET_RATE_LIMITS: dict[str, int] = {
    "fast": 60,
    "balanced": 30,
    "quality": 10,
    "agents": 20,
}
