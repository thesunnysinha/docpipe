"""Tests for configuration loading."""

import os
from pathlib import Path

import pytest

from docpipe.config.loader import load_config
from docpipe.config.settings import DocpipeSettings


def test_default_settings():
    settings = DocpipeSettings()
    assert settings.default_parser == "docling"
    assert settings.default_extractor == "langextract"
    assert settings.chunk_size == 1000
    assert settings.chunk_overlap == 200
    assert settings.server_port == 8000
    assert settings.log_level == "INFO"


def test_env_override(monkeypatch):
    monkeypatch.setenv("DOCPIPE_DEFAULT_PARSER", "custom_parser")
    monkeypatch.setenv("DOCPIPE_CHUNK_SIZE", "500")

    settings = DocpipeSettings()
    assert settings.default_parser == "custom_parser"
    assert settings.chunk_size == 500


def test_load_config_from_yaml(tmp_path):
    config_file = tmp_path / "docpipe.yaml"
    config_file.write_text(
        "default_parser: custom\nchunk_size: 2000\nlog_level: DEBUG\n"
    )

    settings = load_config(config_file)
    assert settings.default_parser == "custom"
    assert settings.chunk_size == 2000
    assert settings.log_level == "DEBUG"


def test_load_config_missing_file():
    settings = load_config("/nonexistent/path.yaml")
    assert settings.default_parser == "docling"


def test_load_config_auto_discover(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "docpipe.yaml"
    config_file.write_text("default_parser: discovered\n")

    settings = load_config()
    assert settings.default_parser == "discovered"
