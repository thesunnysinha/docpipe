"""Shared Pydantic settings behavior for Docpipe configuration sections."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Base for all Docpipe settings sections and their public composition."""

    model_config = {"env_prefix": "DOCPIPE_", "env_nested_delimiter": "__"}
