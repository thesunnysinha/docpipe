"""Tests for dependency-direction architecture guardrails."""

from __future__ import annotations

from pathlib import Path

from scripts.check_architecture import ModuleSizePolicy, check_import_boundaries, check_repository


def test_contract_rejects_vendor_import(tmp_path: Path) -> None:
    module = tmp_path / "src/docpipe/plugins/contracts/vectorstore/reader.py"
    module.parent.mkdir(parents=True)
    module.write_text("from qdrant_client import QdrantClient\n")

    findings = check_import_boundaries(module, tmp_path)

    assert [(finding.code, finding.import_name) for finding in findings] == [
        ("forbidden-contract-import", "qdrant_client")
    ]


def test_coordinator_rejects_concrete_adapter_import(tmp_path: Path) -> None:
    module = tmp_path / "src/docpipe/ingestion/coordinator.py"
    module.parent.mkdir(parents=True)
    module.write_text("from docpipe.vectorstores.pgvector.adapter import PgVectorAdapter\n")

    findings = check_import_boundaries(module, tmp_path)

    assert [(finding.code, finding.import_name) for finding in findings] == [
        ("forbidden-coordinator-import", "docpipe.vectorstores.pgvector.adapter")
    ]


def test_contract_allows_standard_library_and_domain_imports(tmp_path: Path) -> None:
    module = tmp_path / "src/docpipe/plugins/contracts/source/models.py"
    module.parent.mkdir(parents=True)
    module.write_text(
        "from dataclasses import dataclass\nfrom docpipe.core.operation import OperationContext\n"
    )

    assert check_import_boundaries(module, tmp_path) == []


def test_init_rejects_business_functions(tmp_path: Path) -> None:
    module = tmp_path / "src/docpipe/plugins/__init__.py"
    module.parent.mkdir(parents=True)
    module.write_text("def discover_plugins():\n    return []\n")

    findings = check_import_boundaries(module, tmp_path)

    assert [finding.code for finding in findings] == ["init-business-logic"]


def test_repository_allows_only_baselined_init_logic(tmp_path: Path) -> None:
    legacy = tmp_path / "src/docpipe/__init__.py"
    new = tmp_path / "src/docpipe/plugins/__init__.py"
    legacy.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True)
    legacy.write_text("def legacy_api():\n    return None\n")
    new.write_text("def new_business_logic():\n    return None\n")
    policy = ModuleSizePolicy(allowed_init_logic=("src/docpipe/__init__.py",))

    findings = check_repository(tmp_path, policy)

    assert [(item.code, item.path.relative_to(tmp_path).as_posix()) for item in findings] == [
        ("init-business-logic", "src/docpipe/plugins/__init__.py")
    ]
