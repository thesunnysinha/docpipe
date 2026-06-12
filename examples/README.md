# docpipe examples

Sample Docker Compose stacks and a full **environment variable reference** for internal deployments (Delegate, Jingo, Andocs, custom apps).

## Pick a stack

| Example | Use when | Services |
|---------|----------|----------|
| [internal-shared](./internal-shared/) | **Default for shared internal API** — each project passes its own `connection_string` on `/ingest` | docpipe only |
| [pgvector-standard](./pgvector-standard/) | Local dev with bundled Postgres + pgvector | docpipe + db |
| [pgvector-adminer](./pgvector-adminer/) | Same as standard + Adminer DB UI | docpipe + db + adminer |
| [turbovec-local](./turbovec-local/) | No Postgres; file-based vector indices on disk | docpipe only |

```bash
cd examples/internal-shared
cp .env.example .env          # add OPENAI_API_KEY, set DOCPIPE_PASSWORD
docker compose up -d
curl -u admin:your-password http://localhost:8000/health
open http://localhost:8000/admin   # control-plane UI (when enabled)
```

Docker images: `ghcr.io/thesunnysinha/docpipe:balanced` (default), `:slim`, `:quality`, `:agents`. Set `DOPIPE_IMAGE_TAG` in `.env` to override.

---

## Two databases (important)

docpipe uses **two separate storage concepts**:

| Storage | Who owns it | How you configure it |
|---------|-------------|----------------------|
| **Vector / RAG data** (chunks, embeddings) | **Your project** (Delegate, Jingo, …) | `connection_string` + `table_name` on every `/ingest` and `/rag/*` request — or `DOCPIPE_DB_*` as server defaults for health probes |
| **Control-plane metadata** (admin user, optional audit/jobs) | **docpipe operator** | `DOCPIPE_CONTROL_DB_*` — SQLite file in `./data` by default |

docpipe **does not** store document content in the control DB unless you opt in to metadata flags below.

---

## Quick recipes

### Internal shared instance (Kubernetes-style)

```bash
cd examples/internal-shared
cp .env.example .env
# Edit: OPENAI_API_KEY, DOCPIPE_PASSWORD, DOCPIPE_ALLOW_PRIVATE_URLS=true if using MinIO
docker compose up -d
```

Apps call `http://docpipe:8000` with **their own** Postgres URL per request.

### Local dev with pgvector

```bash
cd examples/pgvector-standard
cp .env.example .env
docker compose up -d
# Default vector DB: postgresql://docpipe:docpipe@db:5432/docpipe
```

### Turbovec (no Postgres container)

```bash
cd examples/turbovec-local
cp .env.example .env
docker compose up -d
# Pass vector_backend=turbovec and turbovec_index_dir=/data/indices on ingest
```

---

## Environment variable reference

All docpipe settings use the `DOCPIPE_` prefix (pydantic-settings). Provider keys use standard names (`OPENAI_API_KEY`, etc.).

### Provider API keys

| Variable | Required | What it does |
|----------|----------|--------------|
| `OPENAI_API_KEY` | If using OpenAI embeddings/LLM/Whisper | OpenAI API access |
| `ANTHROPIC_API_KEY` | If using Anthropic LLM | Anthropic API access |
| `GOOGLE_API_KEY` | If using Gemini embeddings/LLM | Google AI access |

### Install profile & plugins

| Variable | Default | What it does |
|----------|---------|--------------|
| `DOCPIPE_PROFILE` | `balanced` | Docker image plugin set: `slim`, `balanced`, `quality`, `agents`, `eval`, `gpu` |
| `DOCPIPE_DEFAULT_PARSER` | `auto` | Default parser when request omits `parser` |
| `DOCPIPE_DEFAULT_PARSER_TIER` | `balanced` | Tier for auto-routing: `fast`, `balanced`, `quality` |
| `DOCPIPE_DEFAULT_CHUNKER` | `recursive` | Default chunker plugin |
| `DOCPIPE_DEFAULT_RERANKER` | `none` | Default reranker (`flashrank`, `bge`, …) |
| `DOCPIPE_DEFAULT_RAG_STRATEGY` | `naive` | Default RAG strategy (`hyde`, `hybrid`, …) |
| `DOCPIPE_DEFAULT_RUNTIME_PRESET` | `balanced` | Default when `preset` omitted on API |
| `DOCPIPE_ENABLED_PARSERS` | all installed | Comma allowlist, e.g. `markitdown,docling` |
| `DOCPIPE_DISABLED_PLUGINS` | none | Comma blocklist, e.g. `pymupdf,mineru` |
| `DOCPIPE_ENABLED_EXTRACTORS` | all | Comma allowlist for extractors |
| `DOCPIPE_ENABLED_CHUNKERS` | all | Comma allowlist for chunkers |
| `DOCPIPE_ENABLED_RERANKERS` | all | Comma allowlist for rerankers |
| `DOCPIPE_ENABLED_EVALUATORS` | all | Comma allowlist for evaluators |

**Runtime presets** (`preset` on `/ingest`, `/rag/query`): `fast`, `balanced`, `quality`, `agents`. Discover via `GET /profiles`.

### Vector store (project data)

| Variable | Default | What it does |
|----------|---------|--------------|
| `DOCPIPE_DB_CONNECTION_STRING` | — | **Server default** Postgres URL for health checks; each API call can override |
| `DOCPIPE_DB_TABLE_NAME` | `docpipe_documents` | Default collection name for health / examples |
| `DOCPIPE_VECTOR_BACKEND` | `pgvector` | `pgvector` or `turbovec` |
| `DOCPIPE_TURBVEC_INDEX_DIR` | `.docpipe/indices` | Directory for turbovec file indices |
| `DOCPIPE_TURBVEC_BIT_WIDTH` | `4` | turbovec quantization width |

Per-request fields (`connection_string`, `table_name`, `vector_backend`) **override** these on every call.

### Embeddings & LLM defaults

| Variable | Default | What it does |
|----------|---------|--------------|
| `DOCPIPE_EMBEDDING_PROVIDER` | — | `openai`, `google`, `ollama`, `huggingface` |
| `DOCPIPE_EMBEDDING_MODEL` | — | Model id for embeddings |
| `DOCPIPE_CHUNK_SIZE` | `1000` | Default chunk size (tokens) |
| `DOCPIPE_CHUNK_OVERLAP` | `200` | Default chunk overlap |
| `DOCPIPE_INGEST_MODE` | `both` | `chunks`, `extractions`, or `both` |

LLM provider/model are set per RAG request; no global `DOCPIPE_LLM_*` in settings (use request body or client defaults).

### Authentication

| Variable | Default | What it does |
|----------|---------|--------------|
| `DOCPIPE_AUTH_ENABLED` | `true` | HTTP Basic Auth on API + `/admin`. Set `false` only on trusted internal networks |
| `DOCPIPE_USERNAME` | `admin` | Basic Auth username (also seeds admin user when control DB enabled) |
| `DOCPIPE_PASSWORD` | `docpipe` | Basic Auth password — **change in production** |

When `DOCPIPE_CONTROL_DB_ENABLED=true`, login is validated against the `admin_users` table after seed.

### Control-plane database (optional metadata)

| Variable | Default | What it does |
|----------|---------|--------------|
| `DOCPIPE_CONTROL_DB_ENABLED` | `false` | Enable SQLite/Postgres for admin + optional audit/jobs |
| `DOCPIPE_CONTROL_DB_URL` | — | Full SQLAlchemy URL; overrides SQLite path |
| `DOCPIPE_CONTROL_DB_PATH` | `/data/docpipe.db` | SQLite file when URL unset (mount `./data:/data`) |
| `DOCPIPE_CONTROL_DB_AUTO_MIGRATE` | `true` | Run Alembic migrations on startup |
| `DOCPIPE_ADMIN_PANEL_ENABLED` | `true` | Serve web UI at `/admin` |
| `DOCPIPE_ADMIN_USERNAME` | falls back to `DOCPIPE_USERNAME` | First-boot superuser name |
| `DOCPIPE_ADMIN_PASSWORD` | falls back to `DOCPIPE_PASSWORD` | First-boot superuser password |
| `DOCPIPE_ADMIN_EMAIL` | `admin@localhost` | Seed email |

**Persistence toggles** (all default `false`; opt in per deployment):

| Variable | What gets stored |
|----------|------------------|
| `DOCPIPE_PERSIST_AUDIT_EVENTS` | Plugin denials and policy events |
| `DOCPIPE_PERSIST_PLUGIN_RESOLUTIONS` | `/plugins/resolve` decisions |
| `DOCPIPE_PERSIST_INGEST_JOBS` | Ingest metadata only (source, table, chunk count — **not** document text) |

### Security (internal — in-process controls)

docpipe is open source: **TLS, ingress, and credential rotation are your responsibility**. docpipe focuses on plugin guardrails, optional audit, rate limits, and URL fetch policy inside your network boundary. Full model: [`docs/INTERNAL_SECURITY.md`](../docs/INTERNAL_SECURITY.md).

| Variable | Default | What it does |
|----------|---------|--------------|
| `DOCPIPE_ALLOW_PRIVATE_URLS` | `false` | Allow parsers to fetch `http://` URLs on private IPs (MinIO, internal object store). **Set `true` only on trusted internal networks** |

### Performance & limits

| Variable | Default | What it does |
|----------|---------|--------------|
| `DOCPIPE_MAX_CONCURRENCY` | `4` | Max parallel pipeline tasks |
| `DOCPIPE_MODEL_CACHE_DIR` | — | Cache dir for CrossEncoder, GLM-OCR, HF models |
| `DOCPIPE_PARSER_CACHE_TTL_SECONDS` | `0` | In-memory parse cache TTL; `0` = off |
| `DOCPIPE_RATE_LIMIT_ENABLED` | `true` | Per-preset POST rate limits (`/ingest`, `/parse`, `/rag/*`) |

### Multi-tenant plugin policy

| Variable | Default | What it does |
|----------|---------|--------------|
| `DOCPIPE_TENANT_PLUGIN_POLICIES` | — | JSON map: `{"team-a":{"enabled_parsers":"markitdown,docling"}}` |
| Request header `X-Docpipe-Tenant-Id` | — | Selects policy entry — **set from trusted server-side callers only**, not end-user clients |

### Observability

| Variable | Default | What it does |
|----------|---------|--------------|
| `DOCPIPE_OTEL_ENABLED` | `false` | OpenTelemetry tracing |
| `DOCPIPE_OTEL_SERVICE_NAME` | `docpipe` | OTEL service name |
| `DOCPIPE_OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP HTTP endpoint |
| `DOCPIPE_HEALTH_CHECK_DB` | `true` | Probe `DOCPIPE_DB_CONNECTION_STRING` in `/health` |
| `DOCPIPE_HEALTH_CHECK_EMBEDDING` | `false` | Probe embedding provider in `/health` |
| `DOCPIPE_PHOENIX_ENABLED` | `false` | Arize Phoenix eval traces |
| `DOCPIPE_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, … |
| `DOCPIPE_HTTP_REQUEST_LOGGING_ENABLED` | `true` | Log each HTTP request |

### Speech-to-text

| Variable | Default | What it does |
|----------|---------|--------------|
| `DOCPIPE_TRANSCRIBE_DEFAULT_BACKEND` | `openai` | `openai`, `vibevoice`, `vibevoice_remote` |
| `DOCPIPE_VIBEVOICE_SERVICE_URL` | — | Remote GPU docpipe for `vibevoice_remote` |

---

## Per-project integration pattern

Each consuming app keeps **its own** vector database. docpipe is stateless for RAG data:

```bash
# Delegate / Jingo / Andocs — pass per assistant or workspace
curl -u admin:your-password -X POST http://docpipe:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "file:///data/uploads/manual.pdf",
    "connection_string": "postgresql://delegate:pass@delegate-db:5432/delegate",
    "table_name": "assistant_abc_docs",
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "preset": "balanced"
  }'
```

Set `preset` per project: `fast` (latency), `balanced` (default), `quality` (scanned PDFs), `agents` (tool-using RAG).

---

## Suggested flag sets

| Deployment | Flags |
|------------|-------|
| **Shared internal API** | `CONTROL_DB_ENABLED=true`, `PERSIST_AUDIT_EVENTS=true`, `ALLOW_PRIVATE_URLS=true`, strong `PASSWORD` |
| **SDK / library only** | `CONTROL_DB_ENABLED=false`, all `PERSIST_*=false` |
| **Single-app local dev** | `pgvector-standard` example + `DB_CONNECTION_STRING` pointing at compose `db` |
| **Compliance / ops** | `PERSIST_AUDIT_EVENTS=true`, `PERSIST_INGEST_JOBS=true`, `PERSIST_PLUGIN_RESOLUTIONS=true` |
| **Max privacy** | All `PERSIST_*=false`; control DB only for admin login |

---

## More docs

- [CONTROL_DB.md](../docs/CONTROL_DB.md) — control-plane database details
- [INTEGRATION.md](../docs/INTEGRATION.md) — client libraries and presets
- [`.env.example`](../.env.example) — full template at repo root
- [INTERNAL_SECURITY.md](../docs/INTERNAL_SECURITY.md) — internal vs deployer security scope
- [SSRF_AUDIT.md](../docs/SSRF_AUDIT.md) — URL source controls
