# docpipe

Unified document parsing, structured extraction, vector ingestion, and RAG pipeline SDK.

[![PyPI](https://img.shields.io/pypi/v/docpipe-sdk)](https://pypi.org/project/docpipe-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/docpipe-sdk)](https://pypi.org/project/docpipe-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/ghcr.io-docpipe-6366f1?logo=docker&logoColor=white)](https://ghcr.io/thesunnysinha/docpipe)
[![Website](https://img.shields.io/badge/docs-docpipe-6366f1)](https://docpipe.sunnysinha.online/docs)

## Overview

docpipe connects document parsing (Docling, [MarkItDown](https://github.com/microsoft/markitdown), GLM-OCR), LLM-based structured extraction (LangExtract + LangChain), vector ingestion (pgvector or optional vector-store plugins), and RAG querying into a single composable pipeline. Optional integrations include Qdrant and S3-compatible adapters, authenticated MCP, opt-in in-memory or Redis RAG response caching, and [AutoGen](https://github.com/microsoft/autogen) agents.

**Four pipelines, composable together:**

1. **Parse** — Unstructured docs → parsed text/markdown
2. **Extract** — Text → structured entities via LLM
3. **Ingest** — Chunks → embeddings → your vector store
4. **RAG** — Questions → grounded answers with citations (six retrieval strategies)

> docpipe does not own your RAG data — each client passes `connection_string` on `/ingest`. An optional control-plane DB (SQLite in Docker) stores admin login and opt-in audit metadata only.

**Full documentation** (install extras, Docker, API reference, RAG strategies, observability, vector stores, plugins): **[docpipe docs](https://docpipe.sunnysinha.online/docs)** · [Source documentation map](docs/README.md) · [Marketing site](https://docpipe.sunnysinha.online)

---

## Install

```bash
pip install docpipe-sdk
# API server + OpenTelemetry (optional)
pip install "docpipe-sdk[server,observability]"
```

Optional extras (`docling`, `openai`, `google`, `pgvector`, `turbovec`, `rag`, `rag-redis`, `mcp-server`, `rerank`, `http`, `all`, …) are listed on the **[Install guide](https://docpipe.sunnysinha.online/docs)**. See [`docs/MCP_SERVER.md`](docs/MCP_SERVER.md) for hosted MCP setup and [`docs/RAG_CACHE.md`](docs/RAG_CACHE.md) for shared RAG caching.

The source and vector-store plugin API is experimental; installed providers use a namespaced `provider`/`options` envelope while legacy request fields remain supported. Qdrant and S3-compatible adapters have conformance coverage. S3 integration tests run against SeaweedFS; MinIO-specific interoperability is not claimed. See the [plugin architecture](docs/architecture/plugins.md), [configuration guide](docs/plugins/configuration.md), and [external plugin example](examples/plugin-package/README.md).

For unreleased commits: `pip install git+https://github.com/thesunnysinha/docpipe.git`

---

## Quick start

```python
import docpipe

# Parse (docling default; markitdown for lightweight Office/PDF → Markdown)
doc = docpipe.parse("invoice.pdf", parser="markitdown")
print(doc.markdown)

# Extract
schema = docpipe.ExtractionSchema(
    description="Extract invoice line items with amounts",
    model_id="gemini-2.5-flash",
)
results = docpipe.extract(doc.text, schema)

# Ingest + RAG (configure your DB + providers)
config = docpipe.IngestionConfig(
    connection_string="postgresql://user:pass@localhost:5432/mydb",
    table_name="invoices",
    embedding_provider="openai",
    embedding_model="text-embedding-3-small",
)
docpipe.ingest("invoice.pdf", config=config)

rag_config = docpipe.RAGConfig(
    connection_string=config.connection_string,
    table_name=config.table_name,
    embedding_provider="openai",
    embedding_model="text-embedding-3-small",
    llm_provider="openai",
    llm_model="gpt-4o",
    strategy="hyde",
    system_prompt=(
        "Answer using ONLY the context below.\n\n"
        "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    ),
    hyde_prompt="Write a passage that answers: {question}",
)
result = docpipe.query("What is the total on the invoice?", config=rag_config)
print(result.answer)

# Optional: AutoGen agents with vector-search tools (pip install "docpipe-sdk[autogen]")
agent_result = docpipe.agent_query(
    "What is the total on the invoice?",
    config=rag_config,
    enable_reviewer=True,
)
print(agent_result.answer)
```

**Agent backends over HTTP.** `POST /agents/query` runs AutoGen by default and LangGraph with `"agent_backend": "langgraph"`. With
`pip install "docpipe-sdk[agents]"` you can also pass `"agent_backend": "runtime"`: the same search (and optional parse) tools,
plus prompt-injection and PII checks on the question, a loop guard that stops repeated or fruitless tool calls, per-tool logging,
and an optional `"session_id"` that continues a conversation (kept in memory by the server process, up to 500 sessions, lost on
restart). Without the extra, requests that omit `agent_backend` behave exactly as before and `runtime` returns an install hint.

**CLI:** `docpipe parse`, `docpipe ingest`, `docpipe rag query`, `docpipe plugins list`, `docpipe profiles list`, `docpipe serve` — see **[CLI & API server](https://docpipe.sunnysinha.online/docs)**.

**Docker (profile tags):**

```bash
docker pull ghcr.io/thesunnysinha/docpipe:balanced   # default production
docker pull ghcr.io/thesunnysinha/docpipe:slim       # lightweight
docker pull ghcr.io/thesunnysinha/docpipe:quality    # OCR + BGE rerank
docker pull ghcr.io/thesunnysinha/docpipe:agents     # AutoGen
docker pull ghcr.io/thesunnysinha/docpipe:mcp        # Streamable HTTP MCP server
```

**pip profiles:** `profile-slim`, `profile-balanced`, `profile-quality`, `profile-agents`, `profile-mcp`, and `profile-gpu`. `profile-gpu` is available for custom installs/builds; there is no published `:gpu` image. See [`.env.example`](.env.example) and [`docs/INTEGRATION.md`](docs/INTEGRATION.md) for the current image/profile matrix.

**Runtime presets** on `/ingest` and `/rag/query`: `preset=fast|balanced|quality|agents`. Discover options via `GET /profiles` and `GET /plugins`.

**Shared Kubernetes API** (one docpipe for Jingo, Andocs, and other apps): manifests in [`k8s/`](k8s/), deploy via `.github/workflows/deploy-k8s.yml`. Consumers call `http://docpipe.docpipe.svc.cluster.local:8000` and pass their own `connection_string` on each `/ingest` and `/rag/*` request (vectors stay in each app's Postgres). See [`env/k8s/DOCPIPE_ENV.example`](env/k8s/DOCPIPE_ENV.example).

**Docker examples** (compose stacks + full env flag reference): [`examples/`](examples/) — start with [`examples/internal-shared/`](examples/internal-shared/) for a shared internal instance.

---

## Learn more

| Topic | Where |
|--------|--------|
| Documentation map | [`docs/README.md`](docs/README.md) |
| Docker examples & env flags | [`examples/README.md`](examples/README.md) |
| App integration (Delegate, presets) | [`docs/INTEGRATION.md`](docs/INTEGRATION.md) |
| Internal security model (open source) | [`docs/INTERNAL_SECURITY.md`](docs/INTERNAL_SECURITY.md) |
| Control-plane DB & `/admin` | [`docs/CONTROL_DB.md`](docs/CONTROL_DB.md) |
| REST API (`/ingest/stream`, `/mcp/*`, `/cost/estimate`, …) | [docs](https://docpipe.sunnysinha.online/docs) |
| Plugins, presets, `/profiles` | [docs](https://docpipe.sunnysinha.online/docs) · `GET /profiles` |
| Speech-to-text (VibeVoice / Whisper) | `POST /transcribe` |
| RAG strategies (`naive`, `hyde`, `hybrid`, …) | [docs](https://docpipe.sunnysinha.online/docs) |
| LightRAG graph sync on ingest | [`docs/LIGHTRAG.md`](docs/LIGHTRAG.md) |
| Observability (OTEL, Prometheus) | [docs](https://docpipe.sunnysinha.online/docs) · `.env.example` |
| Environment variables | [`.env.example`](.env.example) · [`examples/README.md`](examples/README.md) |

---

## License

MIT — see [LICENSE](LICENSE).
