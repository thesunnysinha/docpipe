"""Source defaults, process trust policy, and request override rules."""

from __future__ import annotations

import pytest

from docpipe.config.compatibility import resolve_source_options
from docpipe.config.plugin_options import SourcePluginOptions
from docpipe.config.settings import DocpipeSettings
from docpipe.core.errors import ConfigurationError


def should_map_legacy_source_defaults_to_namespaced_options() -> None:
    settings = DocpipeSettings(
        source_max_bytes=2048,
        source_chunk_bytes=512,
        allow_private_urls=True,
        source_plugin_options={"s3": {"allowed_buckets": ["reports"]}},
    )
    local = resolve_source_options("local", settings)
    http = resolve_source_options("http", settings, temporary_root="/tmp/sources")
    s3 = resolve_source_options("s3", settings)
    assert local.options["max_bytes"] == 2048
    assert http.options["max_bytes"] == 2048
    assert http.options["allow_private"] is True
    assert s3.options == {"allowed_buckets": ["reports"]}


def should_keep_s3_bucket_policy_process_owned() -> None:
    settings = DocpipeSettings(source_plugin_options={"s3": {"allowed_buckets": ["reports"]}})
    with pytest.raises(ConfigurationError, match="allowed_buckets"):
        resolve_source_options(
            "s3",
            settings,
            namespaced=SourcePluginOptions(provider="s3", options={"allowed_buckets": ["other"]}),
        )
    with pytest.raises(ConfigurationError, match="allowed_buckets"):
        resolve_source_options(
            "s3",
            DocpipeSettings(),
            namespaced=SourcePluginOptions(provider="s3", options={"allowed_buckets": ["other"]}),
        )


def should_reject_source_provider_and_legacy_policy_conflicts() -> None:
    settings = DocpipeSettings(source_max_bytes=1024)
    with pytest.raises(ConfigurationError, match="source_max_bytes"):
        resolve_source_options(
            "http",
            settings,
            temporary_root="/tmp/sources",
            namespaced=SourcePluginOptions(provider="http", options={"max_bytes": 2048}),
        )
    with pytest.raises(ConfigurationError, match="source_plugin.provider"):
        resolve_source_options(
            "s3",
            settings,
            namespaced=SourcePluginOptions(provider="http", options={}),
        )


def should_not_widen_http_network_policy_from_request() -> None:
    with pytest.raises(ConfigurationError, match="allow_private_urls"):
        resolve_source_options(
            "http",
            DocpipeSettings(),
            temporary_root="/tmp/sources",
            namespaced=SourcePluginOptions(provider="http", options={"allow_private": True}),
        )
