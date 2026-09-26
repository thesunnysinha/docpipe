"""API server startup command."""

from __future__ import annotations

import sys

import click


@click.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8000, help="Server port")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the docpipe API server."""
    try:
        import uvicorn
    except ImportError:
        click.echo("Server requires uvicorn. Install with: pip install docpipe[server]", err=True)
        sys.exit(1)
    click.echo(f"Starting docpipe server on {host}:{port}")
    uvicorn.run("docpipe.server.app:app", host=host, port=port, reload=reload)
