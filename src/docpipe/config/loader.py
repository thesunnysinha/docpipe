"""YAML and environment-based configuration loader."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from docpipe.config.settings import DocpipeSettings

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATHS = [
    Path("docpipe.yaml"),
    Path("docpipe.yml"),
    Path.home() / ".config" / "docpipe" / "config.yaml",
]


def load_config(path: str | Path | None = None) -> DocpipeSettings:
    """Load configuration from YAML file, env vars, or defaults.

    Priority (highest to lowest):
    1. Environment variables (DOCPIPE_*)
    2. Explicit config file path
    3. Auto-discovered config files (docpipe.yaml in cwd, ~/.config/docpipe/)
    4. Defaults
    """
    yaml_overrides: dict[str, Any] = {}

    if path is not None:
        config_path = Path(path)
        if config_path.exists():
            yaml_overrides = _load_yaml(config_path)
            logger.info("Loaded config from %s", config_path)
        else:
            logger.warning("Config file not found: %s", config_path)
    else:
        for candidate in DEFAULT_CONFIG_PATHS:
            if candidate.exists():
                yaml_overrides = _load_yaml(candidate)
                logger.info("Loaded config from %s", candidate)
                break

    return DocpipeSettings(**yaml_overrides)


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load and parse a YAML config file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}
