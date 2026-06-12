# LightRAG two-phase setup

docpipe supports LightRAG as a **RAG retrieval strategy** and optional **post-ingest graph index sync**.

## Phase 1 — Vector ingest (required)

Use the normal ingest API to chunk and embed into pgvector (or turbovec):

```bash
curl -u admin:docpipe -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "/data/manual.pdf",
    "connection_string": "postgresql://user:pass@db:5432/docpipe",
    "table_name": "manuals",
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "preset": "balanced"
  }'
```

## Phase 2 — LightRAG graph index (optional)

### Option A: sync during ingest

Set `graph_index=true` and provide a writable `lightrag_working_dir`:

```json
{
  "graph_index": true,
  "lightrag_working_dir": "/var/lib/docpipe/lightrag/manuals",
  "...": "..."
}
```

The server inserts parsed markdown/text into LightRAG after vector ingest completes.

### Option B: query-only (manual index)

Build or refresh the LightRAG index out-of-band, then query with:

```json
{
  "strategy": "lightrag",
  "lightrag_working_dir": "/var/lib/docpipe/lightrag/manuals",
  "...": "..."
}
```

Install the extra: `pip install docpipe-sdk[lightrag]`.
