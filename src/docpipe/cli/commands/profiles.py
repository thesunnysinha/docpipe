"""Runtime and installation profile commands."""

from __future__ import annotations

import click


@click.group("profiles")
def profiles() -> None:
    """Install profiles and runtime presets."""


@profiles.command("list")
def profiles_list() -> None:
    """Show install profile, server defaults, and runtime presets."""
    from docpipe.config import get_settings
    from docpipe.profiles.catalog import INSTALL_PROFILES, RUNTIME_PRESETS

    settings = get_settings()
    click.echo(f"Install profile: {settings.profile}")
    click.echo(f"Default parser: {settings.default_parser} (tier={settings.default_parser_tier})")
    click.echo("\nInstall profiles (pip extras):")
    for name, meta in INSTALL_PROFILES.items():
        click.echo(f"  - {name}: {meta['description']}")
    click.echo("\nRuntime presets (API preset=):")
    for name, meta in RUNTIME_PRESETS.items():
        click.echo(f"  - {name}: {meta['description']}")
