# docpipe

Unified document parsing, structured extraction, vector ingestion, and RAG pipeline SDK.

[![PyPI](https://img.shields.io/pypi/v/docpipe-sdk)](https://pypi.org/project/docpipe-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/docpipe-sdk)](https://pypi.org/project/docpipe-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/ghcr.io-docpipe-6366f1?logo=docker&logoColor=white)](https://ghcr.io/thesunnysinha/docpipe)
[![Website](https://img.shields.io/badge/website-docpipe.sunnysinha.online-6366f1)](https://docpipe.sunnysinha.online)

## Overview

docpipe connects document parsing (Docling / GLM-OCR), LLM-based structured extraction (LangExtract + LangChain), vector ingestion (pgvector), and RAG querying into a single composable pipeline.

**Four independent pipelines, composable together:**

1. **Parse** — Unstructured docs → parsed text/markdown via Docling or GLM-OCR
2. **Extract** — Text → structured entities via LLM (LangExtract or LangChain)
3. **Ingest** — Parsed chunks → embeddings → your vector DB (LangChain + pgvector)
4. **RAG** — Questions → grounded answers with source citations (6 retrieval strategies)

> docpipe never stores your data. It connects to your infrastructure and gets out of the way.

---

## Install

```bash
pip install docpipe-sdk                  # Core only
pip install "docpipe-sdk[docling]"       # + Document parsing via Docling (PDF, DOCX, images, ...)
pip install "docpipe-sdk[glm-ocr]"       # + Document parsing via GLM-OCR (state-of-the-art OCR)
pip install "docpipe-sdk[langextract]"   # + Google LangExtract
pip install "docpipe-sdk[openai]"        # + OpenAI embeddings & LLM
pip install "docpipe-sdk[anthropic]"     # + Anthropic Claude
pip install "docpipe-sdk[google]"        # + Google Gemini
pip install "docpipe-sdk[ollama]"        # + Ollama (local models)
pip install "docpipe-sdk[pgvector]"      # + PostgreSQL vector store
pip install "docpipe-sdk[rag]"           # + Hybrid search (BM25 + langchain-classic)
pip install "docpipe-sdk[rerank]"        # + Local reranking (FlashRank)
pip install "docpipe-sdk[server]"        # + FastAPI server
pip install "docpipe-sdk[all]"           # Everything
```

---

## Quick Start

### Parse a document

```python
import docpipe

# Default: Docling parser
doc = docpipe.parse("invoice.pdf")
print(doc.markdown)
print(doc.text)

# GLM-OCR parser (state-of-the-art OCR, best for scanned/image-heavy docs)
doc = docpipe.parse("scanned_report.pdf", parser="glm-ocr")
print(doc.markdown)
```

### Extract structured data

```python
schema = docpipe.ExtractionSchema(
    description="Extract invoice line items with amounts",
    model_id="gemini-2.5-flash",
)
results = docpipe.extract(doc.text, schema)
for r in results:
    print(r.entity_class, r.text, r.attributes)
```

### Full parse + extract pipeline

```python
result = docpipe.run("invoice.pdf", schema)
print(result.parsed.markdown)
print(result.extractions)
```

### Ingest into your vector DB

```python
config = docpipe.IngestionConfig(
    connection_string="postgresql://user:pass@localhost:5432/mydb",
    table_name="invoices",
    embedding_provider="openai",
    embedding_model="text-embedding-3-small",
)
docpipe.ingest("invoice.pdf", config=config)
```

#### Incremental ingestion (skip unchanged files)

```python
config = docpipe.IngestionConfig(
    ...,
    incremental=True,  # skips files already in the DB by SHA-256 hash
)
docpipe.ingest("invoice.pdf", config=config)
# → Skipped 'invoice.pdf' (unchanged, incremental mode)
```

### RAG — ask questions against your documents

```python
rag_config = docpipe.RAGConfig(
    connection_string="postgresql://user:pass@localhost:5432/mydb",
    table_name="invoices",
    embedding_provider="openai",
    embedding_model="text-embedding-3-small",
    llm_provider="openai",
    llm_model="gpt-4o",
    strategy="hyde",   # naive | hyde | multi_query | parent_document | hybrid | auto
)
result = docpipe.rag("What is the total amount on the invoice?", config=rag_config)
print(result.answer)   # grounded answer with inline citations
print(result.sources)  # ["invoice.pdf"]
print(result.chunks)   # retrieved chunks with scores
```

#### Structured RAG output

```python
from pydantic import BaseModel

class InvoiceSummary(BaseModel):
    total: float
    currency: str
    vendor: str

result = docpipe.rag(
    "Summarize the invoice",
    config=docpipe.RAGConfig(..., output_model=InvoiceSummary),
)
summary = result.structured  # InvoiceSummary(total=4250.0, currency='USD', vendor='Acme')
```

#### With reranking

```python
rag_config = docpipe.RAGConfig(
    ...,
    strategy="naive",
    reranker="flashrank",   # local, no API key (pip install "docpipe-sdk[rerank]")
    rerank_top_n=5,
)
```

### Evaluate RAG quality

```python
from docpipe import EvalConfig, EvalQuestion, EvalPipeline

questions = [
    EvalQuestion(
        question="What is the invoice total?",
        expected_answer="$4,250",
        expected_sources=["invoice.pdf"],
    ),
]
cfg = EvalConfig(rag_config=rag_config, questions=questions,
                 metrics=["hit_rate", "answer_similarity"])
result = EvalPipeline(cfg).run()
print(result.metrics.hit_rate)          # 0.9
print(result.metrics.answer_similarity) # 0.85
```

---

## RAG Strategies

| Strategy | How it works | Best for |
|---|---|---|
| `naive` | Vector similarity search | Well-formed queries, fast responses |
| `hyde` | LLM generates hypothetical answer → embed → retrieve | Complex / technical queries (highest accuracy) |
| `multi_query` | Expand into N query variants → union results | Vague or short queries |
| `parent_document` | Retrieve seed chunks → expand context by source | Long documents, context coherence |
| `hybrid` | Dense vector + BM25 keyword via EnsembleRetriever | Exact terms, proper nouns, IDs |
| `auto` | LLM classifies question → dispatches to optimal strategy | Mixed workloads, unknown query types |

---

## CLI

```bash
# Parse
docpipe parse invoice.pdf --format markdown

# Extract
docpipe extract "some text" --schema schema.yaml --model gemini-2.5-flash

# Ingest (with incremental mode)
docpipe ingest invoice.pdf \
    --db "postgresql://..." --table invoices \
    --embedding-provider openai --embedding-model text-embedding-3-small \
    --incremental

# RAG query
docpipe rag query "What is the total?" \
    --db "postgresql://..." --table invoices \
    --strategy hyde \
    --llm-provider openai --llm-model gpt-4o \
    --embedding-provider openai --embedding-model text-embedding-3-small \
    --reranker flashrank

# Evaluate RAG quality
docpipe evaluate run \
    --questions qa.json \
    --db "postgresql://..." --table invoices \
    --llm-provider openai --llm-model gpt-4o \
    --embedding-provider openai --embedding-model text-embedding-3-small \
    --metrics hit_rate,answer_similarity

# Start API server
docpipe serve --port 8000

# List installed plugins
docpipe plugins list
```

### `qa.json` format for evaluation

```json
[
  {
    "question": "What is the invoice total?",
    "expected_answer": "$4,250",
    "expected_sources": ["invoice.pdf"]
  }
]
```

---

## API Server

Start the FastAPI server:

```bash
docpipe serve --host 0.0.0.0 --port 8000
```

Endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check + plugin listing |
| `POST` | `/parse` | Parse a document |
| `POST` | `/extract` | Extract structured data |
| `POST` | `/run` | Parse + extract |
| `POST` | `/ingest` | Ingest into vector DB |
| `DELETE` | `/ingest` | Remove all chunks for a source document |
| `POST` | `/search` | Vector similarity search (supports `filters`) |
| `POST` | `/rag/query` | RAG question answering (supports `history`, `filters`) |
| `POST` | `/rag/stream` | Streaming RAG via Server-Sent Events (SSE) |
| `POST` | `/evaluate/run` | Evaluate RAG quality |
| `GET` | `/plugins` | List registered plugins |

### Conversation history

Pass prior turns to `/rag/query` or `/rag/stream` for multi-turn RAG:

```python
history = [
    {"role": "user", "content": "What is docpipe?"},
    {"role": "assistant", "content": "docpipe is a document processing SDK..."},
]
response = requests.post(f"{BASE}/rag/query", json={..., "history": history})
```

### Metadata filtering

Filter retrieved chunks by document metadata on `/search`, `/rag/query`, and `/rag/stream`:

```python
requests.post(f"{BASE}/rag/query", json={..., "filters": {"source": "report.pdf"}})
```

### Streaming (SSE)

Stream token-by-token answers from `/rag/stream`:

```python
import sseclient, requests

resp = requests.post(f"{BASE}/rag/stream", json={...}, stream=True)
for event in sseclient.SSEClient(resp):
    if event.data == "[DONE]":
        break
    print(event.data, end="", flush=True)
```

### Delete a document

Remove all ingested chunks for a source:

```python
requests.delete(f"{BASE}/ingest", json={
    "connection_string": "postgresql://...",
    "table_name": "docs",
    "source": "reports/q1.pdf",
})
```

---

## Docker

The official image is published to GitHub Container Registry and updated automatically on every release.

```bash
docker pull ghcr.io/thesunnysinha/docpipe:latest
```

### Run the API server

```bash
docker run -p 8000:8000 --env-file .env \
    ghcr.io/thesunnysinha/docpipe:latest
```

### Parse or ingest a document

```bash
# Parse
docker run -v ./data:/data \
    ghcr.io/thesunnysinha/docpipe:latest \
    parse /data/invoice.pdf --format markdown

# Ingest
docker run --env-file .env -v ./data:/data \
    ghcr.io/thesunnysinha/docpipe:latest \
    ingest /data/invoice.pdf \
    --db "postgresql://..." --table invoices \
    --embedding-provider openai --embedding-model text-embedding-3-small
```

### Docker Compose — server + pgvector (zero config)

```bash
cp .env.example .env   # fill in your API key
docker compose up -d
```

```yaml
# docker-compose.yml
services:
  docpipe:
    image: ghcr.io/thesunnysinha/docpipe:latest
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./data:/data
    depends_on:
      db:
        condition: service_healthy

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: docpipe
      POSTGRES_PASSWORD: docpipe
      POSTGRES_DB: docpipe
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U docpipe"]
      interval: 5s
      retries: 5

volumes:
  pgdata:
```

A full-stack variant with Adminer (DB UI) is in [`docker-compose.full.yml`](docker-compose.full.yml).

### Available tags

| Tag | Description |
|---|---|
| `latest` | Most recent build from `main` |
| `0.4.1`, `0.4` | Specific release versions |
| `sha-<hash>` | Exact commit build |

---

## Plugin System

Register custom parsers or extractors via Python entry points:

```toml
# In your package's pyproject.toml
[project.entry-points."docpipe.parsers"]
my_parser = "my_package:MyParser"

[project.entry-points."docpipe.extractors"]
my_extractor = "my_package:MyExtractor"
```

Implement the `BaseParser` or `BaseExtractor` protocol (structural subtyping — no inheritance required):

```python
class MyParser:
    name = "my_parser"

    def parse(self, source: str, **kwargs) -> docpipe.ParsedDocument: ...
    async def aparse(self, source: str, **kwargs) -> docpipe.ParsedDocument: ...
    def is_available(self) -> bool: ...
    def supported_formats(self) -> list[str]: ...
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for a full walkthrough.

---

## Supported Providers

| Component | Providers |
|---|---|
| **Parsing** | Docling (PDF, DOCX, XLSX, PPTX, HTML, images), GLM-OCR (state-of-the-art multimodal OCR) |
| **Extraction** | LangExtract (Google), LangChain `with_structured_output` |
| **Embeddings** | OpenAI, Google Gemini, Ollama, HuggingFace |
| **Vector store** | PostgreSQL + pgvector |
| **LLM (RAG)** | OpenAI, Anthropic Claude, Google Gemini, Ollama |
| **Reranking** | FlashRank (local), Cohere |

---

## License

MIT — see [LICENSE](LICENSE).
