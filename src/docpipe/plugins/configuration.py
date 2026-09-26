"""Transport-safe and typed plugin configuration boundaries."""

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

_PROVIDER_PATTERN = r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"


class TypedPluginConfig(BaseModel):
    """Base for immutable provider-specific configuration models."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PluginConfig(TypedPluginConfig):
    """JSON-compatible configuration passed to a plugin factory."""

    provider: str = Field(
        min_length=1,
        pattern=_PROVIDER_PATTERN,
        description="Registered plugin identifier that selects the provider implementation.",
    )
    options: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Provider-specific options containing only JSON-compatible values.",
    )


def validation_option_path(error: ValidationError, *, category: str) -> str:
    """Return the first invalid option path without serializing its value."""
    first = error.errors(include_input=False)[0]
    location = ".".join(str(part) for part in first["loc"])
    return f"{category}.options.{location}" if location else f"{category}.options"
