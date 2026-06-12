"""Domain-specific chunking presets."""

from __future__ import annotations

from typing import Any

CHUNK_METHOD_SETTINGS: dict[str, dict[str, Any]] = {
    "paper": {
        "separators": ["\n## ", "\n### ", "\n\n", "\n", " "],
        "chunk_size": 1500,
        "chunk_overlap": 150,
    },
    "laws": {
        "separators": ["\nSection ", "\nArticle ", "\n\n", "\n"],
        "chunk_size": 2000,
        "chunk_overlap": 100,
    },
    "book": {
        "separators": ["\nChapter ", "\n\n", "\n"],
        "chunk_size": 2000,
        "chunk_overlap": 200,
    },
    "qa": {
        "separators": ["\nQ:", "\n\n", "\n"],
        "chunk_size": 500,
        "chunk_overlap": 50,
    },
    "manual": {
        "separators": ["\n# ", "\n## ", "\n\n", "\n"],
        "chunk_size": 800,
        "chunk_overlap": 100,
    },
    "table": {
        "separators": ["\n\n", "\n"],
        "chunk_size": 500,
        "chunk_overlap": 0,
    },
    "presentation": {
        "separators": ["\n---", "\n\n", "\n"],
        "chunk_size": 600,
        "chunk_overlap": 50,
    },
}
