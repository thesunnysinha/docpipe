"""Tests for the plugin registry."""

import pytest

from docpipe.core.errors import ExtractorNotFoundError, ParserNotFoundError
from docpipe.registry.registry import PluginRegistry
from tests.conftest import MockExtractor, MockParser


def test_register_and_get_parser():
    registry = PluginRegistry.get()
    registry.register_parser("mock", MockParser)

    parser = registry.get_parser("mock")
    assert parser.name == "mock"
    assert isinstance(parser, MockParser)


def test_register_and_get_extractor():
    registry = PluginRegistry.get()
    registry.register_extractor("mock", MockExtractor)

    extractor = registry.get_extractor("mock")
    assert extractor.name == "mock"
    assert isinstance(extractor, MockExtractor)


def test_get_unknown_parser_raises():
    registry = PluginRegistry.get()
    with pytest.raises(ParserNotFoundError, match="nonexistent"):
        registry.get_parser("nonexistent")


def test_get_unknown_extractor_raises():
    registry = PluginRegistry.get()
    with pytest.raises(ExtractorNotFoundError, match="nonexistent"):
        registry.get_extractor("nonexistent")


def test_list_parsers():
    registry = PluginRegistry.get()
    registry.register_parser("a", MockParser)
    registry.register_parser("b", MockParser)

    parsers = registry.list_parsers()
    assert "a" in parsers
    assert "b" in parsers


def test_list_extractors():
    registry = PluginRegistry.get()
    registry.register_extractor("x", MockExtractor)

    extractors = registry.list_extractors()
    assert "x" in extractors


def test_parser_info():
    registry = PluginRegistry.get()
    registry.register_parser("mock", MockParser)

    info = registry.parser_info("mock")
    assert info["name"] == "mock"
    assert info["available"] is True
    assert "text" in info["formats"]


def test_extractor_info():
    registry = PluginRegistry.get()
    registry.register_extractor("mock", MockExtractor)

    info = registry.extractor_info("mock")
    assert info["name"] == "mock"
    assert info["available"] is True


def test_singleton_pattern():
    r1 = PluginRegistry.get()
    r2 = PluginRegistry.get()
    assert r1 is r2


def test_reset():
    r1 = PluginRegistry.get()
    PluginRegistry.reset()
    r2 = PluginRegistry.get()
    assert r1 is not r2


def test_parser_kwargs_forwarded():
    registry = PluginRegistry.get()
    registry.register_parser("mock", MockParser)

    parser = registry.get_parser("mock", custom_option="value")
    assert parser._options == {"custom_option": "value"}
