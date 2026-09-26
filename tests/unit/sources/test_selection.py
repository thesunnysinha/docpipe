"""Catalog-based source resolver selection and lifecycle ownership."""

from __future__ import annotations

from pathlib import Path

import pytest

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.plugin_options import SourcePluginOptions
from docpipe.config.settings import DocpipeSettings
from docpipe.plugins.errors import (
    PluginConfigurationError,
    UnsafeSourceError,
    UnsupportedSourceError,
)
from docpipe.sources.selection import SourceResolverSelector, source_provider


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("report.pdf", "local"),
        ("/data/report.pdf", "local"),
        ("file:///data/report.pdf", "local"),
        ("http://example.org/report.pdf", "http"),
        ("https://example.org/report.pdf", "http"),
        ("s3://bucket/report.pdf", "s3"),
    ],
)
def test_provider_selection_depends_only_on_parsed_scheme(source: str, expected: str) -> None:
    assert source_provider(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "https+http://example.org/report.pdf",
        "\x00report.pdf",
        "s3://[malformed/report.pdf",
    ],
)
def test_unknown_or_malformed_sources_are_rejected(source: str) -> None:
    with pytest.raises(UnsupportedSourceError):
        source_provider(source)


@pytest.mark.asyncio
async def test_selected_local_handle_is_owned_by_operation_scope(tmp_path: Path) -> None:
    document = tmp_path / "report.txt"
    document.write_text("content", encoding="utf-8")
    settings = DocpipeSettings(source_allowed_roots=(tmp_path,))
    runtime = build_runtime(settings)

    async with runtime:
        selector = SourceResolverSelector(runtime)
        async with selector.resolve(str(document)) as handle, handle:
            assert await handle.materialize() == document.resolve()

        with pytest.raises(RuntimeError, match="not active"):
            handle.open()


@pytest.mark.asyncio
async def test_provider_hint_in_query_cannot_override_scheme(tmp_path: Path) -> None:
    pytest.importorskip("boto3")
    settings = DocpipeSettings(
        source_allowed_roots=(tmp_path,),
        source_temporary_root=tmp_path / "downloads",
        source_plugin_options={
            "s3": {"allowed_buckets": ["bucket"], "temporary_root": str(tmp_path)}
        },
    )
    runtime = build_runtime(settings)
    async with runtime:
        selector = SourceResolverSelector(runtime)
        with pytest.raises(UnsafeSourceError) as failure:
            async with selector.resolve("s3://bucket/key?provider=local"):
                pass
    assert getattr(failure.value, "code", None) == "source_unsafe"


@pytest.mark.asyncio
async def test_http_selection_rejects_world_readable_temporary_root(
    tmp_path: Path,
) -> None:
    downloads = tmp_path / "downloads"
    downloads.mkdir(mode=0o755)
    downloads.chmod(0o755)
    settings = DocpipeSettings(source_temporary_root=downloads)
    runtime = build_runtime(settings)

    async with runtime:
        with pytest.raises(PluginConfigurationError, match="permissions"):
            async with SourceResolverSelector(runtime).resolve("https://example.org/report.pdf"):
                pass


@pytest.mark.asyncio
async def test_source_plugin_provider_must_match_uri_scheme(tmp_path: Path) -> None:
    settings = DocpipeSettings(source_allowed_roots=(tmp_path,))
    runtime = build_runtime(settings)

    async with runtime:
        with pytest.raises(Exception, match="source_plugin.provider"):
            async with SourceResolverSelector(runtime).resolve(
                "https://example.org/report.pdf",
                options=SourcePluginOptions(provider="s3", options={}),
            ):
                pass


@pytest.mark.asyncio
async def test_unknown_source_option_fails_after_provider_selection_with_path(
    tmp_path: Path,
) -> None:
    document = tmp_path / "report.txt"
    document.write_text("content", encoding="utf-8")
    settings = DocpipeSettings(
        source_allowed_roots=(tmp_path,),
        source_plugin_options={"local": {"future_option": True}},
    )
    runtime = build_runtime(settings)

    async with runtime:
        with pytest.raises(PluginConfigurationError) as failure:
            async with SourceResolverSelector(runtime).resolve(str(document)):
                pass

    assert failure.value.context["field"] == "source_plugin.options.future_option"
