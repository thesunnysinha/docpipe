"""S3 factory resolves references without retaining secrets in options."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("boto3")

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.credentials import EnvironmentCredentialResolver
from docpipe.plugins.errors import PluginConfigurationError
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.sources.s3.factory import create_plugin


def should_resolve_references_only_after_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fake_client(service: str, **kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("boto3.client", fake_client)
    options = {
        "allowed_buckets": ["documents"],
        "temporary_root": str(tmp_path),
        "access_key_id_ref": {"kind": "environment", "name": "S3_ACCESS"},
        "secret_access_key_ref": {"kind": "environment", "name": "S3_SECRET"},
    }
    config = PluginConfig(provider="s3", options=options)
    create_plugin(
        config,
        context=PluginFactoryContext(
            blocking_runner=BoundedBlockingRunner(1),
            credentials=EnvironmentCredentialResolver(
                {"S3_ACCESS": "access-private", "S3_SECRET": "secret-private"}
            ),
        ),
    )

    assert captured["aws_access_key_id"] == "access-private"
    assert captured["aws_secret_access_key"] == "secret-private"
    assert "secret-private" not in config.model_dump_json()


def should_reject_literal_credentials_with_nested_field(tmp_path: Path) -> None:
    with pytest.raises(PluginConfigurationError) as failure:
        create_plugin(
            PluginConfig(
                provider="s3",
                options={
                    "allowed_buckets": ["documents"],
                    "temporary_root": str(tmp_path),
                    "aws_secret_access_key": "private-value",
                },
            ),
            context=PluginFactoryContext(blocking_runner=BoundedBlockingRunner(1)),
        )

    assert failure.value.context["field"] == "source_plugin.options.aws_secret_access_key"
    assert "private-value" not in str(failure.value)
