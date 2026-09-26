"""Public configuration models and backward-compatible loader aliases."""

from docpipe.config.loader import load_config
from docpipe.config.settings import DocpipeSettings

get_settings = load_config

__all__ = ["DocpipeSettings", "get_settings", "load_config"]
