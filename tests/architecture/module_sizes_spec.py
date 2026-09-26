"""Tests for source-size architecture guardrails."""

from __future__ import annotations

from pathlib import Path

from scripts.check_architecture import ModuleSizePolicy, check_module_size, check_repository


def _write_module(path: Path, logical_lines: int) -> None:
    path.write_text("\n".join(f"value_{line} = {line}" for line in range(logical_lines)))


def test_module_at_target_has_no_findings(tmp_path: Path) -> None:
    module = tmp_path / "focused.py"
    _write_module(module, 250)

    assert check_module_size(module, ModuleSizePolicy()) == []


def test_module_above_target_requires_review(tmp_path: Path) -> None:
    module = tmp_path / "review.py"
    _write_module(module, 301)

    findings = check_module_size(module, ModuleSizePolicy())

    assert [(finding.severity, finding.code) for finding in findings] == [
        ("warning", "module-size-review")
    ]


def test_new_module_above_hard_limit_fails(tmp_path: Path) -> None:
    module = tmp_path / "monolith.py"
    _write_module(module, 351)

    findings = check_module_size(module, ModuleSizePolicy())

    assert [(finding.severity, finding.code) for finding in findings] == [
        ("error", "module-size-limit")
    ]


def test_grandfathered_module_may_not_grow(tmp_path: Path) -> None:
    module = tmp_path / "legacy.py"
    _write_module(module, 352)
    policy = ModuleSizePolicy(baseline={str(module): 351})

    findings = check_module_size(module, policy)

    assert [(finding.severity, finding.code) for finding in findings] == [
        ("error", "module-size-growth")
    ]


def test_comments_and_blank_lines_do_not_count(tmp_path: Path) -> None:
    module = tmp_path / "comments.py"
    module.write_text("# comment\n\nvalue = 1\n" * 251)

    policy = ModuleSizePolicy(review=250)

    assert check_module_size(module, policy).pop().logical_lines == 251


def test_repository_uses_relative_baseline_paths(tmp_path: Path) -> None:
    module = tmp_path / "src/docpipe/legacy.py"
    module.parent.mkdir(parents=True)
    _write_module(module, 351)
    policy = ModuleSizePolicy(baseline={"src/docpipe/legacy.py": 351})

    assert check_repository(tmp_path, policy) == []


def test_repository_checks_source_and_test_modules(tmp_path: Path) -> None:
    source = tmp_path / "src/docpipe/too_large.py"
    test = tmp_path / "tests/unit/large_spec.py"
    source.parent.mkdir(parents=True)
    test.parent.mkdir(parents=True)
    _write_module(source, 351)
    _write_module(test, 351)

    findings = check_repository(tmp_path, ModuleSizePolicy())

    assert {finding.path.relative_to(tmp_path).as_posix() for finding in findings} == {
        "src/docpipe/too_large.py",
        "tests/unit/large_spec.py",
    }
