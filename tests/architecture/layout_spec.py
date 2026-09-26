"""Keep the behavioral test suite modular as integrations grow."""

from __future__ import annotations

from pathlib import Path


def should_keep_test_modules_under_two_hundred_lines() -> None:
    """Push large fixture collections and unrelated behaviors into focused modules."""
    tests_root = Path(__file__).resolve().parents[1]
    oversized: dict[str, int] = {}
    for path in tests_root.rglob("*.py"):
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > 200:
            oversized[str(path.relative_to(tests_root))] = lines
    assert oversized == {}
