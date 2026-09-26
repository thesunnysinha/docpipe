"""Published plugin compatibility rules remain explicit and verifiable."""

from pathlib import Path


def should_publish_plugin_api_compatibility_policy() -> None:
    """Make the support promises visible to plugin authors before API v1 stabilizes."""
    repository_root = Path(__file__).resolve().parents[2]
    policy_path = repository_root / "docs" / "plugins" / "compatibility.md"

    assert policy_path.is_file()
    policy = policy_path.read_text(encoding="utf-8").lower()
    assert "experimental" in policy
    assert "major" in policy
    assert "minor" in policy
    assert "patch" in policy
    assert "deprecation" in policy
    assert "qdrant" in policy
    assert "minio" in policy
