# Contributing to docpipe

Thanks for your interest in contributing. docpipe is a plugin-based Python SDK — most contributions fall into one of: adding a parser, adding an extractor, improving the RAG pipeline, or improving the HTTP server and observability.

## Documentation in this repo

| Doc | Purpose |
|-----|---------|
| [README.md](README.md) | Overview, install, quick start |
| [CONTRIBUTING.md](CONTRIBUTING.md) | This file — development and PR workflow |
| [.env.example](.env.example) | All `DOCPIPE_*` environment variables |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [pyproject.toml](pyproject.toml) | Package metadata and optional extras |

**User-facing guides** (install extras, Docker, REST API, RAG strategies, observability, turbovec): **[docpipe docs](https://docpipe.sunnysinha.online/docs)** on the marketing site. Keep detailed tables and compose examples there; update [`lib/docs-content.ts`](https://github.com/thesunnysinha/docpipe-site/blob/main/lib/docs-content.ts) in the [docpipe-site](https://github.com/thesunnysinha/docpipe-site) repo when the public API changes.

Canonical source on GitHub: [github.com/thesunnysinha/docpipe](https://github.com/thesunnysinha/docpipe)

## Development setup

```bash
git clone https://github.com/thesunnysinha/docpipe.git
cd docpipe
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,all]"
python run.py test    # or: pytest tests/unit/ -v
python run.py lint
```

## Project structure

```
src/docpipe/
├── core/           # Pydantic types, protocols, pipeline orchestrator, errors
├── parsers/        # Document parsing plugins (Docling, GLM-OCR, …)
├── extractors/     # Extraction plugins (LangExtract, LangChain)
├── ingestion/      # Chunk → embed → vector store
├── vectorstores/   # pgvector (default) and optional turbovec backends
├── rag/            # RAG pipeline (six retrieval strategies)
├── observability/  # OTEL, metrics, structured logging
├── http/           # DocpipeClient for the REST API
├── eval/           # RAG evaluation pipeline
├── cli/            # Click commands
├── server/         # FastAPI app
├── registry/       # Plugin discovery
└── config/         # Settings (DOCPIPE_* env vars)
```

## Adding a new parser plugin

Implement the `BaseParser` protocol from `docpipe.core.parser`. Structural subtyping means **no inheritance** is required — just implement the right methods.

```python
# my_package/my_parser.py
from docpipe.core.types import DocumentFormat, ParsedDocument
import asyncio

class MyParser:
    name = "my_parser"

    def parse(self, source: str, **kwargs) -> ParsedDocument:
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

Register in your package's `pyproject.toml`:

```toml
[project.entry-points."docpipe.parsers"]
my_parser = "my_package.my_parser:MyParser"
```

After `pip install my_package`, docpipe auto-discovers it:

```bash
docpipe plugins list
```

Add a unit test that mocks the underlying library so no external dep is needed.

## Adding a new extractor plugin

Same pattern — implement `BaseExtractor` from `docpipe.core.extractor` and register under `[project.entry-points."docpipe.extractors"]`. See an existing extractor under `src/docpipe/extractors/` for reference.

## Running tests

```bash
python run.py test
# or
pytest tests/unit/ -v
pytest tests/integration/ -m "not requires_api_key and not requires_pgvector"
pytest tests/ --cov=src/docpipe --cov-report=term-missing
```

Test markers:

| Marker | Requires |
|--------|----------|
| `requires_docling` | `docpipe-sdk[docling]` |
| `requires_langextract` | `docpipe-sdk[langextract]` |
| `requires_pgvector` | PostgreSQL with pgvector |
| `requires_api_key` | LLM API key in environment |
| `requires_rag` | RAG extra, DB, and API key |
| `requires_turbovec` | `docpipe-sdk[turbovec]` |

## Code style

```bash
python run.py lint
# or
ruff check src/
ruff format src/
mypy src/docpipe/ --ignore-missing-imports
```

All must pass before opening a PR. CI runs on Python 3.10–3.13.

Conventions:

- `from __future__ import annotations` in source files
- Lazy-import optional deps inside methods with clear `ImportError` messages
- Pipeline classes expose sync and async (`asyncio.to_thread`) where applicable
- Raise `ConfigurationError` with an install hint when an optional extra is missing

## Commit messages

```
feat: add example retrieval strategy
fix: handle empty ParsedDocument in IngestionPipeline
docs: update .env.example for new setting
```

Prefix: `feat | fix | docs | chore | refactor | test`

## Opening a pull request

1. Fork [thesunnysinha/docpipe](https://github.com/thesunnysinha/docpipe) and branch from `main`
2. Run `python run.py lint` and `python run.py test`
3. Describe what changed and **why**
4. Link issues (`Closes #123`)
5. Wait for CI to pass

If you change HTTP fields or env vars, mention whether [docpipe-site](https://github.com/thesunnysinha/docpipe-site) docs need a follow-up PR.

## Releasing (maintainers only)

See [CLAUDE.md](CLAUDE.md) in this repo:

```bash
python run.py lint
python run.py test
python run.py release <version>   # bumps version, updates CHANGELOG, tags
git push origin main --tags
gh release create v<version> --title "v<version>" --notes "..."
```

PyPI publish runs via GitHub Actions on `v*` tags (trusted publishing).

## Bugs and feature requests

Open a [GitHub issue](https://github.com/thesunnysinha/docpipe/issues).

For bugs, include Python version, install command, minimal reproduction, and full traceback.
