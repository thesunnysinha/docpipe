## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `/Users/sunny/Desktop/Projects/docpipe/.venv/bin/python -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current

## Project Structure

- `src/docpipe/server/app.py` — FastAPI app; all HTTP endpoints
- `src/docpipe/rag/pipeline.py` — RAGPipeline; 6 retrieval strategies
- `src/docpipe/ingestion/pipeline.py` — IngestionPipeline; chunking + PGVector
- `src/docpipe/core/types.py` — all shared Pydantic models
- `src/docpipe/config/settings.py` — DocpipeSettings (env prefix: `DOCPIPE_`)

## Commands

```bash
.venv/bin/python -m docpipe serve  # start FastAPI server on :8000
docker compose up -d               # start server + pgvector DB
.venv/bin/pytest tests/            # full test suite
pip install -e ".[all]"            # install all extras (docling, OCR, etc.)
python run.py test                 # run pytest via run.py
python run.py lint                 # ruff check + format check
python run.py serve                # start FastAPI dev server
```

## Release Process

**Always do all steps before pushing a release:**

1. Update `README.md` with any new endpoints, fields, or behaviour changes
2. Update `docpipe-site` (`/Users/sunny/Desktop/Projects/docpipe-site`) — playground UI must reflect new API fields
3. Run `python run.py lint` — CI will fail if ruff errors exist (line length 100, SIM117, unused imports)
4. Run `python run.py test` — all tests must pass
5. Run `python run.py release <version>` — bumps `_version.py` + `pyproject.toml`, commits, tags
6. `git push origin main --tags`
7. Create GitHub Release from the tag: `gh release create v<version> --title "v<version>" --notes "..."` — this triggers the PyPI publish workflow

## Key Patterns

- `source` field in `IngestRequest` is file path or URL — NOT file bytes
- `table_name` is pgvector collection name; must be valid PG identifier (no dashes, can't start with digit); validated by `validate_table_name` in `core/types.py` — apply to all request models with `table_name`
- `DELETE /ingest` removes chunks by source via raw psycopg2 SQL (not LangChain)
- `RAGQueryRequest.history` — list of `{role, content}` dicts for multi-turn conversation
- `RAGQueryRequest.filters` / `SearchRequest.filters` — pgvector metadata filter dict; use `or None` guard before passing to `similarity_search_with_score()`
