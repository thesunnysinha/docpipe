"""Plugin manifests must validate through the base Pydantic dependency only."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from docpipe.plugins.manifest_models import PluginManifest


def should_validate_a_manifest_without_jsonschema_installed() -> None:
    """Keep manifest discovery usable without adding a schema engine to base installs."""
    repository_root = Path(__file__).resolve().parents[3]
    script = f"""
import importlib.abc
import json
import sys
sys.path.insert(0, {str(repository_root / "src")!r})
class BlockJsonSchema(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'jsonschema' or fullname.startswith('jsonschema.'):
            raise ModuleNotFoundError('jsonschema is intentionally unavailable')
sys.meta_path.insert(0, BlockJsonSchema())
from docpipe.plugins.manifest import parse_manifest
manifest = json.dumps({{
    'schema_version': 1,
    'plugins': [{{
        'name': 'example',
        'category': 'vectorstore',
        'description': 'Example adapter.',
    }}],
}})
result = parse_manifest(manifest)
assert len(result) == 1
"""

    subprocess.run([sys.executable, "-c", script], cwd=repository_root, check=True)


def should_keep_pydantic_validation_aligned_with_published_manifest_schema() -> None:
    """Keep external authoring tools and runtime discovery on the same manifest rules."""
    repository_root = Path(__file__).resolve().parents[3]
    schema_path = repository_root / "src" / "docpipe" / "plugins" / "manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    documents = [
        (
            {
                "schema_version": 1,
                "plugins": [
                    {
                        "name": "example",
                        "category": "vectorstore",
                        "description": "Example adapter.",
                    }
                ],
            },
            True,
        ),
        ({"schema_version": True, "plugins": [{"name": "example"}]}, False),
        ({"schema_version": 1, "plugins": []}, False),
        (
            {
                "schema_version": 1,
                "plugins": [
                    {"name": "Example", "category": "vectorstore", "description": "Invalid name."}
                ],
            },
            False,
        ),
        (
            {
                "schema_version": 1,
                "plugins": [
                    {
                        "name": "example",
                        "category": "vectorstore",
                        "description": "Example adapter.",
                        "unexpected": True,
                    }
                ],
            },
            False,
        ),
    ]

    for document, expected in documents:
        schema_accepts = validator.is_valid(document)
        try:
            PluginManifest.model_validate(document)
        except ValueError:
            pydantic_accepts = False
        else:
            pydantic_accepts = True

        assert schema_accepts is expected
        assert pydantic_accepts is expected
