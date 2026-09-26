"""Tenant, URL, and trusted-proxy security settings."""

import ipaddress

from pydantic import Field, field_validator

from docpipe.config.settings_sections.base import Settings


class SecuritySettings(Settings):
    """Security boundaries applied by HTTP and plugin-resolution services."""

    rate_limit_enabled: bool = Field(
        default=True, description="Apply bounded in-memory rate limiting to expensive HTTP routes."
    )
    rate_limit_trusted_proxy_cidrs: tuple[str, ...] = Field(
        default=(),
        description=(
            "Proxy CIDRs allowed to supply X-Forwarded-For for rate limiting. "
            "Only configure proxies that overwrite or append the connecting client address."
        ),
    )
    tenant_plugin_policies: str | None = Field(
        default=None, description="JSON tenant-to-plugin policy map used to restrict plugin access."
    )
    tenant_identity_map: dict[str, str] = Field(
        default_factory=dict,
        description="Maps authenticated Basic Auth usernames to tenant IDs.",
    )
    allow_private_urls: bool = Field(
        default=False,
        description="Permit private or loopback source URLs; enable only for trusted deployments.",
    )

    @field_validator("rate_limit_trusted_proxy_cidrs")
    @classmethod
    def validate_rate_limit_trusted_proxy_cidrs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize configured proxy networks and reject malformed entries."""
        try:
            return tuple(str(ipaddress.ip_network(cidr, strict=False)) for cidr in value)
        except ValueError as error:
            raise ValueError(
                "rate_limit_trusted_proxy_cidrs must contain valid IP CIDRs"
            ) from error
