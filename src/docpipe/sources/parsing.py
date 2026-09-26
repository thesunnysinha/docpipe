"""Application coordinator joining source resolution to parser compatibility."""

from __future__ import annotations

from docpipe.bootstrap.runtime import DocpipeRuntime
from docpipe.config.plugin_options import SourcePluginOptions
from docpipe.core.types import ParsedDocument
from docpipe.parsers.input_adapter import ParserInputAdapter
from docpipe.sources.selection import SourceResolverSelector


class SourceParser:
    """Parse one external source while owning all temporary resources."""

    def __init__(self, runtime: DocpipeRuntime) -> None:
        self._runtime = runtime
        self._selector = SourceResolverSelector(runtime)
        self._adapter = ParserInputAdapter(runtime.blocking_runner)

    async def parse(
        self,
        parser: object,
        source: str,
        *,
        options: SourcePluginOptions | None = None,
    ) -> ParsedDocument:
        """Resolve ``source`` and adapt its handle to ``parser`` safely."""
        # Source resolution remains policy-gated even during a vector-store
        # rollback. Passing raw request sources to legacy parsers would bypass
        # allowed-root, SSRF, and download-size protections.
        async with self._selector.resolve(source, options=options) as handle:
            return await self._adapter.parse(parser, handle)
