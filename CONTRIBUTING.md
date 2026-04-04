# Contributing to docpipe

Thanks for your interest in contributing. docpipe is a plugin-based Python SDK — most contributions fall into one of: adding a new parser, adding a new extractor, improving the RAG pipeline, or improving the core infrastructure.

## Development Setup

```bash
git clone https://github.com/thesunnysinha/docpipe
cd docpipe
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"        # installs pytest, ruff, mypy, httpx
pytest tests/unit/ -v          # confirm all 53 tests pass
```

## Project Structure

```
src/docpipe/
├── core/          # Pydantic types, protocols, pipeline orchestrator, errors
├── parsers/       # Document parsing plugins (DoclingParser)
├── extractors/    # Extraction plugins (LangExtract, LangChain)
├── ingestion/     # Chunk → embed → vector DB pipeline (IngestionPipeline)
├── rag/           # RAG query pipeline (RAGPipeline, 5 strategies)
├── eval/          # RAG evaluation pipeline (EvalPipeline)
├── cli/           # Click commands
├── server/        # FastAPI endpoints
├── registry/      # Plugin auto-discovery via Python entry points
└── config/        # Pydantic settings + YAML loader
```

## Adding a New Parser Plugin

Implement the `BaseParser` protocol from `docpipe.core.parser`. Structural subtyping means **no inheritance** is required — just implement the right methods.

```python
# my_package/my_parser.py
from docpipe.core.types import DocumentFormat, ParsedDocument
import asyncio

class MyParser:
    name = "my_parser"

    def parse(self, source: str, **kwargs) -> ParsedDocument:
        # Do your parsing here
        return ParsedDocument(
            source=source,
            format=DocumentFormat.PDF,
            text="parsed text",
            markdown="# parsed text",
        )

    async def aparse(self, source: str, **kwargs) -> ParsedDocument:
        return await asyncio.to_thread(self.parse, source, **kwargs)

    def parse_batch(self, sources: list[str]) -> list[ParsedDocument]:
        return [self.parse(s) for s in sources]

    def is_available(self) -> bool:
        try:
            import my_dependency  # noqa: F401
            return True
        except ImportError:
            return False

    def supported_formats(self) -> list[str]:
        return ["pdf", "docx"]
```

Register it in your package's `pyproject.toml`:

```toml
[project.entry-points."docpipe.parsers"]
my_parser = "my_package.my_parser:MyParser"
```

After `pip install my_package`, docpipe auto-discovers it:

```bash
docpipe plugins list
# Parsers:
#   - docling (available)
#   - my_parser (available)
```

Add a unit test that mocks the underlying library so no external dep is needed:

```python
from unittest.mock import patch, MagicMock

@patch("my_package.my_parser.my_dependency")
def test_my_parser(mock_dep):
    from my_package.my_parser import MyParser
    parser = MyParser()
    result = parser.parse("test.pdf")
    assert result.format.value == "pdf"
```

## Adding a New Extractor Plugin

Same pattern, implement `BaseExtractor` from `docpipe.core.extractor`:

```python
class MyExtractor:
    name = "my_extractor"

    def extract(self, text: str, schema, **kwargs) -> list:
        # Return list[ExtractionResult]
        ...

    async def aextract(self, text: str, schema, **kwargs) -> list:
        return await asyncio.to_thread(self.extract, text, schema, **kwargs)

    def is_available(self) -> bool: ...
```

Register:

```toml
[project.entry-points."docpipe.extractors"]
my_extractor = "my_package:MyExtractor"
```

## Running Tests

```bash
# Unit tests — no external deps, no API keys needed
pytest tests/unit/ -v

# Skip tests that need real infrastructure
pytest tests/integration/ -m "not requires_api_key and not requires_pgvector"

# With coverage
pytest tests/ --cov=src/docpipe --cov-report=term-missing
```

Test markers:

| Marker | Requires |
|---|---|
| `requires_docling` | `docpipe-sdk[docling]` installed |
| `requires_langextract` | `docpipe-sdk[langextract]` installed |
| `requires_pgvector` | Running PostgreSQL with pgvector |
| `requires_api_key` | LLM API key in environment |
| `requires_rag` | RAG extra, DB, and API key |

## Code Style

```bash
ruff check src/           # lint
ruff format src/          # format (line length 100)
mypy src/docpipe/ --ignore-missing-imports  # type check
```

All three must pass before opening a PR. CI enforces this on Python 3.10–3.13.

Key conventions:
- Use `from __future__ import annotations` in all source files
- Lazy-import optional deps inside methods (not at module level) with helpful `ImportError` messages
- Follow the `EMBEDDING_PROVIDERS` / `LLM_PROVIDERS` dict pattern for dynamic provider loading
- All pipeline classes expose both `method()` and `amethod()` (async via `asyncio.to_thread`)
- Raise `ConfigurationError` with an install hint when an optional dep is missing

## Commit Message Convention

```
feat: add ColBERT retrieval strategy to RAGPipeline
fix: handle empty ParsedDocument in IngestionPipeline
docs: add example for incremental ingestion
chore: bump langchain-core to 0.4
refactor: extract _create_embeddings into shared util
test: add unit tests for hybrid RAG strategy
```

Prefix: `feat | fix | docs | chore | refactor | test`

## Opening a Pull Request

1. Fork the repo and create a branch from `main`
2. Make your changes — all unit tests must pass, ruff and mypy must be clean
3. Describe what changed and **why** in the PR description
4. Link the issue it closes (`Closes #123`)
5. CI runs automatically on push — wait for it to go green

## Releasing (maintainers only)

```bash
./scripts/release.sh 0.2.0
git push origin main --tags
```

GitHub Actions publishes to PyPI automatically via trusted publisher (OIDC) when a `v*` tag is pushed. No token needed.

## Reporting Bugs / Requesting Features

Open a [GitHub issue](https://github.com/thesunnysinha/docpipe/issues).

For bugs, include:
- Python version and OS
- Exact install command (`pip install docpipe-sdk[...]`)
- Minimal reproduction snippet
- Full traceback
