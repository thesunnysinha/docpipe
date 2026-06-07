# docpipe

Unified document parsing, structured extraction, vector ingestion, and RAG pipeline SDK.

[![PyPI](https://img.shields.io/pypi/v/docpipe-sdk)](https://pypi.org/project/docpipe-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/docpipe-sdk)](https://pypi.org/project/docpipe-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/ghcr.io-docpipe-6366f1?logo=docker&logoColor=white)](https://ghcr.io/thesunnysinha/docpipe)
[![Website](https://img.shields.io/badge/docs-docpipe-6366f1)](https://docpipe.sunnysinha.online/docs)

## Overview

docpipe connects document parsing (Docling / GLM-OCR), LLM-based structured extraction (LangExtract + LangChain), vector ingestion (pgvector or optional turbovec), and RAG querying into a single composable pipeline.

**Four pipelines, composable together:**

1. **Parse** — Unstructured docs → parsed text/markdown
2. **Extract** — Text → structured entities via LLM
3. **Ingest** — Chunks → embeddings → your vector store
4. **RAG** — Questions → grounded answers with citations (six retrieval strategies)

> docpipe never stores your data. It connects to your infrastructure and gets out of the way.

**Full documentation** (install extras, Docker, API reference, RAG strategies, observability, turbovec, plugins): **[docpipe docs](https://docpipe.sunnysinha.online/docs)** · [Marketing site](https://docpipe.sunnysinha.online)

---

## Install

```bash
pip install docpipe-sdk
# API server + OpenTelemetry (optional)
pip install "docpipe-sdk[server,observability]"
```

Optional extras (`docling`, `openai`, `google`, `pgvector`, `turbovec`, `rag`, `rerank`, `http`, `all`, …) are listed on the **[Install guide](https://docpipe.sunnysinha.online/docs)**.

For unreleased commits: `pip install git+https://github.com/thesunnysinha/docpipe.git`

---

## Quick start

```python
import docpipe

# Parse
doc = docpipe.parse("invoice.pdf")
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
```

**CLI:** `docpipe parse`, `docpipe ingest`, `docpipe rag query`, `docpipe serve` — see **[CLI & API server](https://docpipe.sunnysinha.online/docs)**.

**Docker:** `docker pull ghcr.io/thesunnysinha/docpipe:latest` — compose examples and env vars are in the **[Docker guide](https://docpipe.sunnysinha.online/docs)** and [`.env.example`](.env.example). Compose files set **CPU/RAM limits** (4 CPU / 4 GiB standalone) and `DOCPIPE_MAX_CONCURRENCY=2` so ingest/RAG cannot exhaust the host.

**Shared Kubernetes API** (one docpipe for Jingo, Andocs, and other apps): manifests in [`k8s/`](k8s/), deploy via `.github/workflows/deploy-k8s.yml`. Consumers call `http://docpipe.docpipe.svc.cluster.local:8000` and pass their own `connection_string` on each `/ingest` and `/rag/*` request (vectors stay in each app's Postgres). See [`env/k8s/DOCPIPE_ENV.example`](env/k8s/DOCPIPE_ENV.example).

---

## Learn more

| Topic | Where |
|--------|--------|
| Install extras & providers | [docs](https://docpipe.sunnysinha.online/docs) |
| REST API (`/ingest`, `/rag/query`, `/rag/stream`, `/transcribe`, …) | [docs](https://docpipe.sunnysinha.online/docs) |
| Speech-to-text ([VibeVoice ASR](https://github.com/microsoft/VibeVoice) or OpenAI Whisper) | `POST /transcribe` · backends: `openai`, `vibevoice`, `vibevoice_remote` |
| RAG strategies (`naive`, `hyde`, `hybrid`, `auto`, …) | [docs](https://docpipe.sunnysinha.online/docs) |
| Observability (OTEL, Prometheus, JSON logs) | [docs](https://docpipe.sunnysinha.online/docs) · `.env.example` |
| turbovec (local file indices) | [docs](https://docpipe.sunnysinha.online/docs) |
| Custom parsers / extractors | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Environment variables | [`.env.example`](.env.example) · [config reference](https://docpipe.sunnysinha.online/docs) |

---

## License

MIT — see [LICENSE](LICENSE).
