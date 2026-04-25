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
```

## Key Patterns

- `source` field in `IngestRequest` is file path or URL — NOT file bytes
- `table_name` is pgvector collection name; must be valid PG identifier (no dashes, can't start with digit)
- No DELETE endpoint — chunks removed via raw SQL on pgvector table
- No conversation history in `RAGQueryRequest` — queries are stateless
