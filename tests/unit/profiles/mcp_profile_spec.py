"""Install-profile metadata for the optional hosted MCP feature."""

from __future__ import annotations

from docpipe.config.settings import DocpipeSettings
from docpipe.profiles.catalog import INSTALL_PROFILES


def test_mcp_profile_is_a_distinct_opt_in_install_profile() -> None:
    profile = INSTALL_PROFILES["mcp"]

    assert DocpipeSettings(profile="mcp").profile == "mcp"
    assert profile["pip_extra"] == "profile-mcp"
    assert profile["docker_tag"] == "mcp"
