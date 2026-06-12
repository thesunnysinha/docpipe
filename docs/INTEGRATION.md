# Integrating apps with docpipe (Delegate, Jingo, Andocs)

## Shared internal API pattern

One docpipe instance on your cluster network; **each app passes its own `connection_string`** on every `/ingest` and `/rag/*` call. Vector data stays in each project's Postgres — docpipe does not centralize RAG storage unless you point every client at the same DB.

Docker example: [`examples/internal-shared/`](../examples/internal-shared/) · Full env reference: [`examples/README.md`](../examples/README.md)

## Discovery flow

1. `GET /profiles` — install profile, runtime presets, server defaults
2. `GET /plugins` — installed plugins with `available`, `allowed`, `tier`, `license`
3. `POST /plugins/resolve` — recommendation for a file + goal (optional)
4. Pass `preset` on `/ingest`, `/rag/query`, `/agents/query` or set explicit parser/chunker/reranker fields

## Python client

```python
from docpipe.client.integration import DocpipeClient

with DocpipeClient(
    "http://docpipe.docpipe.svc.cluster.local:8000",
    username="admin",
    password="...",
) as client:
    presets = client.available_preset_names()
    rec = client.resolve(source="invoice.pdf", preset="balanced")
    client.ingest(
        source="s3://bucket/invoice.pdf",
        connection_string="postgresql://delegate:pass@delegate-db:5432/delegate",
        table_name="assistant_docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        preset="balanced",
    )
```

## Streaming ingest (SSE)

For long jobs, use `POST /ingest/stream` — progress events: `resolve` → `parse` → `chunk` → `complete`.

```bash
curl -u admin:your-password -N -X POST http://docpipe:8000/ingest/stream \
  -H "Content-Type: application/json" \
  -d '{"source":"file:///data/doc.pdf","connection_string":"postgresql://...","table_name":"docs","embedding_provider":"openai","embedding_model":"text-embedding-3-small","preset":"balanced"}'
```

## MCP tools (agents)

- `GET /mcp/tools` — tool descriptors for `docpipe_parse`, `docpipe_rag_query`
- `POST /mcp/call` — invoke a tool with JSON arguments

## Cost estimation

`POST /cost/estimate` — heuristic parse seconds and embedding USD by `preset` + `page_count` (planning only, not billing).

## Delegate assistant settings (recommended UX)

| UI label | API |
|----------|-----|
| Fast | `preset=fast` |
| Balanced | `preset=balanced` |
| Quality | `preset=quality` |
| Agents | `preset=agents` on `/agents/query` |

Store the user's choice on the assistant record; pass it on every ingest/RAG call.

## Install profiles (operators)

| pip extra | Docker tag | Use |
|-----------|------------|-----|
| `profile-slim` | `:slim` | Sidecars, MarkItDown-only |
| `profile-balanced` | `:balanced` | **Default** K8s / internal shared |
| `profile-quality` | `:quality` | OCR + BGE rerank |
| `profile-agents` | `:agents` | AutoGen |
| `profile-gpu` | `:gpu` | MinerU / PaddleOCR |

```bash
pip install "docpipe-sdk[profile-balanced]"
docker pull ghcr.io/thesunnysinha/docpipe:balanced
```

## Control-plane database (optional)

Separate from vector/RAG data. Stores admin login + optional audit/job metadata when enabled.

| Variable | Purpose |
|----------|---------|
| `DOCPIPE_CONTROL_DB_ENABLED` | SQLite/Postgres for operator metadata |
| `DOCPIPE_PERSIST_AUDIT_EVENTS` | Plugin policy audit log |
| `DOCPIPE_PERSIST_INGEST_JOBS` | Ingest job metadata (no document content) |

Admin UI: `GET /admin` (Basic Auth). See [`docs/CONTROL_DB.md`](CONTROL_DB.md).

## Security (internal)

docpipe is open source — you handle TLS, ingress, and secrets. Inside your cluster, docpipe provides plugin allowlists, optional audit, rate limits, and URL fetch policy. See [`INTERNAL_SECURITY.md`](INTERNAL_SECURITY.md).

- Pass `X-Docpipe-Tenant-Id` from **your backend only** (not mobile/browser clients).
- Each app owns its `connection_string`; vectors are not centralized unless you choose to.

## Guardrails

```bash
DOCPIPE_PROFILE=balanced
DOCPIPE_DEFAULT_PARSER=auto
DOCPIPE_DEFAULT_PARSER_TIER=balanced
DOCPIPE_DEFAULT_RUNTIME_PRESET=balanced
DOCPIPE_DISABLED_PLUGINS=pymupdf,mineru
DOCPIPE_ENABLED_PARSERS=markitdown,docling
DOCPIPE_ALLOW_PRIVATE_URLS=true   # internal Docker / MinIO only
```

## CLI

```bash
docpipe plugins list
docpipe profiles list
docpipe resolve invoice.pdf --goal ingest
```
