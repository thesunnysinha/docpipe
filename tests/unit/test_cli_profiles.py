"""CLI profile and resolve commands."""

from __future__ import annotations

from click.testing import CliRunner

from docpipe.cli.main import cli


def test_profiles_list_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["profiles", "list"])
    assert result.exit_code == 0
    assert "Install profile:" in result.output
    assert "balanced" in result.output


def test_resolve_command_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["resolve", "sample.pdf", "--goal", "ingest"])
    assert result.exit_code == 0
    assert '"recommended"' in result.output
    assert '"parser"' in result.output
