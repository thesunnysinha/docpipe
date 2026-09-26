"""Document parsing, extraction, and combined pipeline commands."""

from __future__ import annotations

import json
from pathlib import Path

import click


@click.command()
@click.argument("file")
@click.option("--parser", default="docling", help="Parser to use")
@click.option(
    "--format", "output_format", default="markdown", type=click.Choice(["markdown", "text", "json"])
)
@click.option("--output", "-o", default=None, help="Output file (default: stdout)")
def parse(file: str, parser: str, output_format: str, output: str | None) -> None:
    """Parse a document into structured text."""
    from docpipe.registry.registry import PluginRegistry

    result = PluginRegistry.get().get_parser(parser).parse(file)
    if output_format == "markdown":
        content = result.markdown or result.text
    elif output_format == "text":
        content = result.text
    else:
        content = result.model_dump_json(indent=2)
    if output:
        Path(output).write_text(content)
        click.echo(f"Output written to {output}")
    else:
        click.echo(content)


@click.command()
@click.argument("text_or_file")
@click.option("--schema", "schema_file", required=True, help="Schema YAML file")
@click.option("--extractor", default="langextract", help="Extractor to use")
@click.option("--model", "model_id", required=True, help="LLM model ID")
@click.option("--output", "-o", default=None, help="Output file (default: stdout)")
def extract(
    text_or_file: str, schema_file: str, extractor: str, model_id: str, output: str | None
) -> None:
    """Extract structured data from text or a file."""
    import yaml

    from docpipe.core.types import ExtractionSchema
    from docpipe.registry.registry import PluginRegistry

    with open(schema_file) as f:
        schema_data = yaml.safe_load(f)
    schema_data["model_id"] = model_id
    schema = ExtractionSchema(**schema_data)
    text = Path(text_or_file).read_text() if Path(text_or_file).exists() else text_or_file
    results = PluginRegistry.get().get_extractor(extractor).extract(text, schema)
    content = json.dumps([r.model_dump() for r in results], indent=2, default=str)
    if output:
        Path(output).write_text(content)
        click.echo(f"Output written to {output}")
    else:
        click.echo(content)


@click.command("run")
@click.argument("file")
@click.option("--schema", "schema_file", required=True, help="Schema YAML file")
@click.option("--parser", default="docling", help="Parser to use")
@click.option("--extractor", default="langextract", help="Extractor to use")
@click.option("--model", "model_id", required=True, help="LLM model ID")
@click.option("--output", "-o", default=None, help="Output file (default: stdout)")
def run_pipeline(
    file: str, schema_file: str, parser: str, extractor: str, model_id: str, output: str | None
) -> None:
    """Run the full pipeline: parse + extract."""
    import yaml

    from docpipe.core.pipeline import Pipeline
    from docpipe.core.types import ExtractionSchema

    with open(schema_file) as f:
        schema_data = yaml.safe_load(f)
    schema_data["model_id"] = model_id
    result = Pipeline(parser=parser, extractor=extractor).run(file, ExtractionSchema(**schema_data))
    content = result.model_dump_json(indent=2)
    if output:
        Path(output).write_text(content)
        click.echo(f"Output written to {output}")
    else:
        click.echo(content)
