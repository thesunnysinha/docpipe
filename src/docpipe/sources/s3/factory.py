"""Selected-only Boto3 construction for the S3 source plugin."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from docpipe.plugins.configuration import PluginConfig, validation_option_path
from docpipe.plugins.errors import PluginConfigurationError, PluginDependencyError
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.sources.s3.resolver import S3SourceResolver
from docpipe.sources.s3.schemas import S3SourceConfig
from docpipe.sources.s3.transfer import S3Client


def create_plugin(config: PluginConfig, *, context: PluginFactoryContext) -> S3SourceResolver:
    """Resolve secret references and create a scoped client only when selected."""
    if config.provider != "s3":
        raise PluginConfigurationError("S3 source factory received another provider", plugin="s3")
    try:
        typed = S3SourceConfig.model_validate(config.options)
    except ValidationError as error:
        raise PluginConfigurationError(
            "S3 source configuration is invalid",
            plugin="s3",
            context={"field": validation_option_path(error, category="source_plugin")},
        ) from error
    try:
        import boto3
        from botocore.config import Config
    except ImportError as error:
        raise PluginDependencyError(
            "S3 source dependency is unavailable",
            plugin="s3",
            hint="Install docpipe-sdk[s3]",
        ) from error

    kwargs: dict[str, Any] = {
        "endpoint_url": typed.endpoint_url,
        "region_name": typed.region_name,
        "config": Config(
            connect_timeout=typed.connect_timeout,
            read_timeout=typed.read_timeout,
            retries={"max_attempts": 1},
            s3={"addressing_style": "path"},
        ),
    }
    if typed.access_key_id_ref is not None:
        if context.credentials is None:
            raise PluginConfigurationError("S3 credential resolver is unavailable", plugin="s3")
        assert typed.secret_access_key_ref is not None
        kwargs["aws_access_key_id"] = context.credentials.resolve(
            typed.access_key_id_ref
        ).get_secret_value()
        kwargs["aws_secret_access_key"] = context.credentials.resolve(
            typed.secret_access_key_ref
        ).get_secret_value()
        if typed.session_token_ref is not None:
            kwargs["aws_session_token"] = context.credentials.resolve(
                typed.session_token_ref
            ).get_secret_value()
    try:
        client: S3Client = boto3.client("s3", **kwargs)
    except Exception as error:
        raise PluginConfigurationError("S3 client could not be created", plugin="s3") from error
    return S3SourceResolver(typed, client=client, runner=context.blocking_runner, owns_client=True)
