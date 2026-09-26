"""Check repository dependency and module-size architecture constraints."""

from __future__ import annotations

import ast
import json
import sys
import tokenize
from argparse import ArgumentParser
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ArchitectureFinding:
    """One actionable architecture-policy violation."""

    path: Path
    code: str
    severity: str
    message: str
    logical_lines: int | None = None
    import_name: str | None = None


@dataclass(frozen=True, slots=True)
class ModuleSizePolicy:
    """Configured source-size thresholds and legacy baselines."""

    target: int = 250
    review: int = 300
    hard_limit: int = 350
    baseline: dict[str, int] = field(default_factory=dict)
    allowed_init_logic: tuple[str, ...] = ()


def check_module_size(path: Path, policy: ModuleSizePolicy) -> list[ArchitectureFinding]:
    """Return size-policy findings for one Python module.

    Blank lines and comment-only lines are ignored. Docstrings count because they
    contribute to the size a maintainer must understand.
    """
    ignored = {
        tokenize.ENCODING,
        tokenize.ENDMARKER,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.NEWLINE,
        tokenize.NL,
        tokenize.COMMENT,
    }
    with path.open("rb") as source:
        logical_lines = {
            token.start[0]
            for token in tokenize.tokenize(source.readline)
            if token.type not in ignored
        }

    count = len(logical_lines)
    baseline = policy.baseline.get(str(path))
    if baseline is not None and count > baseline:
        return [
            ArchitectureFinding(
                path=path,
                code="module-size-growth",
                severity="error",
                logical_lines=count,
                message=f"grandfathered module grew from {baseline} to {count} logical lines",
            )
        ]
    if baseline is None and count > policy.hard_limit:
        return [
            ArchitectureFinding(
                path=path,
                code="module-size-limit",
                severity="error",
                logical_lines=count,
                message=f"new module has {count} logical lines; limit is {policy.hard_limit}",
            )
        ]
    if baseline is None and count > policy.review:
        return [
            ArchitectureFinding(
                path=path,
                code="module-size-review",
                severity="warning",
                logical_lines=count,
                message=f"module has {count} logical lines and requires architecture review",
            )
        ]
    return []


def check_import_boundaries(
    path: Path, repository_root: Path, *, allow_init_logic: bool = False
) -> list[ArchitectureFinding]:
    """Return dependency-direction findings for one Python module."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    relative = path.relative_to(repository_root).as_posix()
    findings: list[ArchitectureFinding] = []

    if path.name == "__init__.py" and not allow_init_logic:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                findings.append(
                    ArchitectureFinding(
                        path=path,
                        code="init-business-logic",
                        severity="error",
                        message="package initializers may re-export names but not define functions",
                    )
                )
                break

    imports = _import_names(tree)
    if "/plugins/contracts/" in relative:
        for import_name in imports:
            if _is_forbidden_contract_import(import_name):
                findings.append(
                    ArchitectureFinding(
                        path=path,
                        code="forbidden-contract-import",
                        severity="error",
                        import_name=import_name,
                        message=f"plugin contract imports external implementation {import_name!r}",
                    )
                )

    if path.name == "coordinator.py":
        concrete_roots = ("docpipe.vectorstores.", "docpipe.sources.")
        for import_name in imports:
            if import_name.startswith(concrete_roots):
                findings.append(
                    ArchitectureFinding(
                        path=path,
                        code="forbidden-coordinator-import",
                        severity="error",
                        import_name=import_name,
                        message=f"coordinator imports concrete adapter {import_name!r}",
                    )
                )
    return findings


def check_repository(
    repository_root: Path, policy: ModuleSizePolicy
) -> list[ArchitectureFinding]:
    """Return architecture findings for production and test Python modules."""
    absolute_baseline = {
        str(repository_root / relative_path): limit
        for relative_path, limit in policy.baseline.items()
    }
    resolved_policy = ModuleSizePolicy(
        target=policy.target,
        review=policy.review,
        hard_limit=policy.hard_limit,
        baseline=absolute_baseline,
        allowed_init_logic=policy.allowed_init_logic,
    )
    findings: list[ArchitectureFinding] = []
    for top_level in ("src", "tests"):
        source_root = repository_root / top_level
        if not source_root.exists():
            continue
        for path in sorted(source_root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            findings.extend(check_module_size(path, resolved_policy))
            relative = path.relative_to(repository_root).as_posix()
            findings.extend(
                check_import_boundaries(
                    path,
                    repository_root,
                    allow_init_logic=relative in policy.allowed_init_logic,
                )
            )
    return findings


def _import_names(tree: ast.AST) -> list[str]:
    """Collect absolute imports from an abstract syntax tree."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def _is_forbidden_contract_import(import_name: str) -> bool:
    """Return whether an import crosses the dependency boundary for contracts."""
    root = import_name.partition(".")[0]
    if root in sys.stdlib_module_names:
        return False
    if import_name == "docpipe.core" or import_name.startswith("docpipe.core."):
        return False
    return not (import_name == "docpipe.plugins" or import_name.startswith("docpipe.plugins."))


def _load_policy(path: Path | None) -> ModuleSizePolicy:
    """Load a module-size policy from a JSON baseline file."""
    if path is None or not path.exists():
        return ModuleSizePolicy()
    data = json.loads(path.read_text(encoding="utf-8"))
    return ModuleSizePolicy(
        target=int(data.get("target", 250)),
        review=int(data.get("review", 300)),
        hard_limit=int(data.get("hard_limit", 350)),
        baseline={str(key): int(value) for key, value in data.get("baseline", {}).items()},
        allowed_init_logic=tuple(str(path) for path in data.get("allowed_init_logic", [])),
    )


def main() -> int:
    """Run repository architecture checks and return a shell exit status."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    policy = _load_policy(args.baseline)
    findings = check_repository(args.root.resolve(), policy)
    for finding in findings:
        print(f"{finding.severity}: {finding.path}: {finding.code}: {finding.message}")
    return int(any(finding.severity == "error" for finding in findings))


if __name__ == "__main__":
    raise SystemExit(main())
