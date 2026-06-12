"""Optional LightRAG index sync after vector ingest."""

from __future__ import annotations

import logging

from docpipe.core.errors import ConfigurationError
from docpipe.core.types import ParsedDocument

logger = logging.getLogger(__name__)


def sync_parsed_document(*, working_dir: str, parsed: ParsedDocument) -> None:
    """Insert parsed text into a LightRAG working directory."""
    try:
        from lightrag import LightRAG
    except ImportError as err:
        raise ConfigurationError(
            "graph_index requires lightrag. Install with: pip install docpipe-sdk[lightrag]"
        ) from err

    text = parsed.markdown or parsed.text
    if not text.strip():
        logger.warning("Skipping LightRAG sync for empty document: %s", parsed.source)
        return

    rag = LightRAG(working_dir=working_dir)
    rag.insert(text)
    logger.info("Synced %s into LightRAG working_dir=%s", parsed.source, working_dir)
