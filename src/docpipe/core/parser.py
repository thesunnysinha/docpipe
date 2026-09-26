"""Structural interface for single and batch document parser plugins.

Parser implementations are expected to accept the inputs and options they
advertise through their own configuration and format declarations. The core
protocol intentionally leaves vendor-specific keyword arguments and parser
failure types implementation-defined; runtime adapters normalize failures at
their public boundaries.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from docpipe.core.types import ParsedDocument


@runtime_checkable
class BaseParser(Protocol):
    """Structural contract for parsers that operate on document sources.

    Implementations should keep sync methods blocking and async methods
    awaitable, and return :class:`ParsedDocument` instances for successful
    inputs. A parser's :meth:`supported_formats` and :meth:`is_available`
    describe its declared capability, not a guarantee that any particular
    document will parse successfully.
    """

    name: str

    def parse(self, source: str, **kwargs: object) -> ParsedDocument:
        """Parse one document synchronously from a parser-supported source.

        Args:
            source: Source string accepted by this implementation, typically a
                local path or URL.
            **kwargs: Parser-specific options; accepted names and defaults are
                implementation-defined.

        Returns:
            Parsed document with content and source metadata.
        """
        ...

    async def aparse(self, source: str, **kwargs: object) -> ParsedDocument:
        """Parse one document asynchronously from a supported source.

        Args:
            source: Source string accepted by this implementation.
            **kwargs: Parser-specific options; accepted names and defaults are
                implementation-defined.

        Returns:
            Parsed document with content and source metadata.
        """
        ...

    def parse_batch(self, sources: list[str], **kwargs: object) -> list[ParsedDocument]:
        """Parse each source in a batch using implementation-defined scheduling.

        Args:
            sources: Source strings accepted by this parser.
            **kwargs: Parser-specific options shared across the batch.

        Returns:
            Parsed documents corresponding to the supplied inputs; ordering and
            partial-failure behavior are determined by the implementation.
        """
        ...

    @classmethod
    def is_available(cls) -> bool:
        """Report whether this parser's required runtime dependencies are usable.

        Returns:
            ``True`` when the implementation considers its parser backend
            available; this does not validate input documents or credentials.
        """
        ...

    @classmethod
    def supported_formats(cls) -> list[str]:
        """List file-format identifiers the implementation advertises.

        Returns:
            Format strings, conventionally extensions such as ``".pdf"``.
            Actual format coverage remains parser/backend dependent.
        """
        ...
