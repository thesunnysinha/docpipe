"""Install profiles, runtime presets, and plugin guardrails."""

from docpipe.profiles.catalog import INSTALL_PROFILES, RUNTIME_PRESETS
from docpipe.profiles.guardrails import assert_plugin_allowed, build_plugins_payload
from docpipe.profiles.presets import apply_defaults_and_preset, list_runtime_presets
from docpipe.profiles.resolve import resolve_recommendation

__all__ = [
    "INSTALL_PROFILES",
    "RUNTIME_PRESETS",
    "apply_defaults_and_preset",
    "assert_plugin_allowed",
    "build_plugins_payload",
    "list_runtime_presets",
    "resolve_recommendation",
]
