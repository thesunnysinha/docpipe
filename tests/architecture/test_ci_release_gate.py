"""Release jobs enforce plugin boundaries rather than hiding type failures."""

from __future__ import annotations

from pathlib import Path

import yaml

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[2]


def test_ci_requires_full_suite_and_strict_plugin_typing() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["test"]["steps"]
    commands = "\n".join(str(step.get("run", "")) for step in steps)

    assert "pytest -q" in commands
    assert "ruff format --check src tests scripts/benchmark_plugin_foundation.py" in commands
    assert "ruff check src tests scripts/benchmark_plugin_foundation.py" in commands
    assert "mypy" in commands and "--strict" in commands
    assert all(step.get("continue-on-error") is not True for step in steps)


def test_ci_runs_vector_conformance_and_docker_profile_matrix() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]

    assert "vector-conformance" in jobs
    assert "docker-profiles" in jobs
    assert jobs["docker-profiles"]["strategy"]["matrix"]["profile"] == [
        "slim",
        "balanced",
        "quality",
        "agents",
    ]
    assert "qdrant-conformance" in jobs
    assert "s3-conformance" in jobs


def test_ci_runs_for_pull_requests_to_any_target_branch() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    events = workflow.get("on", workflow.get(True))

    assert events is not None
    assert not (events.get("pull_request") or {}).get("branches")


def test_starts_each_docker_profile_and_retains_performance_results() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    docker_steps = jobs["docker-profiles"]["steps"]
    smoke = next(step for step in docker_steps if step.get("name") == "Smoke-test server startup")
    smoke_command = str(smoke["run"])
    assert "docker run --detach" in smoke_command
    assert "docpipe-test:${{ matrix.profile }}" in smoke_command
    assert "DOCPIPE_HEALTH_CHECK_DB=false" in smoke_command
    assert "http://127.0.0.1:8000/health" in smoke_command

    vector_steps = jobs["vector-conformance"]["steps"]
    benchmark = next(
        step for step in vector_steps if step.get("name") == "Record plugin performance baseline"
    )
    assert "benchmark_plugin_foundation.py" in benchmark["run"]
    assert any(
        "plugin-foundation-benchmark.json" in str(step)
        for step in vector_steps
        if "upload-artifact" in str(step)
    )


def test_reference_integrations_are_optional_and_not_in_curated_profiles() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = metadata["project"]
    optional = project["optional-dependencies"]
    assert any("qdrant-client" in requirement for requirement in optional["qdrant"])
    assert any("boto3" in requirement for requirement in optional["s3"])
    assert not any(
        name in requirement.lower()
        for requirement in project["dependencies"]
        for name in ("qdrant", "boto3", "jsonschema")
    )
    for profile in ("profile-slim", "profile-balanced", "profile-quality", "profile-agents"):
        assert all(
            "qdrant" not in requirement and ",s3" not in requirement
            for requirement in optional[profile]
        )
