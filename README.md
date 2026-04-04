# docpipe

Unified document parsing, structured extraction, vector ingestion, and RAG pipeline SDK.

[![PyPI](https://img.shields.io/pypi/v/docpipe-sdk)](https://pypi.org/project/docpipe-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/docpipe-sdk)](https://pypi.org/project/docpipe-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Website](https://img.shields.io/badge/website-docpipe.sunnysinha.online-6366f1)](https://docpipe.sunnysinha.online)

## Overview

docpipe connects document parsing (Docling), LLM-based structured extraction (LangExtract + LangChain), vector ingestion (pgvector via LangChain), and RAG querying into a single composable pipeline.

**Four independent pipelines, composable together:**

1. **Parse** — Unstructured docs → parsed text/markdown via Docling
2. **Extract** — Text → structured entities via LLM (LangExtract or LangChain)
3. **Ingest** — Parsed chunks → embeddings → your vector DB (LangChain + pgvector)
4. **RAG** — Questions → grounded answers with source citations (5 retrieval strategies)

> docpipe never stores your data. It connects to your infrastructure and gets out of the way.

---

## Install

```bash
pip install docpipe-sdk                  # Core only
pip install "docpipe-sdk[docling]"       # + Document parsing (PDF, DOCX, images, ...)
pip install "docpipe-sdk[langextract]"   # + Google LangExtract
pip install "docpipe-sdk[openai]"        # + OpenAI embeddings & LLM
pip install "docpipe-sdk[google]"        # + Google Gemini
pip install "docpipe-sdk[ollama]"        # + Ollama (local models)
pip install "docpipe-sdk[pgvector]"      # + PostgreSQL vector store
pip install "docpipe-sdk[rag]"           # + Hybrid search (BM25)
pip install "docpipe-sdk[rerank]"        # + Local reranking (FlashRank)
pip install "docpipe-sdk[server]"        # + FastAPI server
pip install "docpipe-sdk[all]"           # Everything
```

---

## Quick Start

### Parse a document

```python
import docpipe

doc = docpipe.parse("invoice.pdf")
print(doc.markdown)
print(doc.text)
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
    strategy="hyde",   # naive | hyde | multi_query | parent_document | hybrid
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
    reranker="flashrank",   # local, no API key (pip install docpipe-sdk[rerank])
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
print(result.metrics.hit_rate)         # 0.9
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
# or via Docker
docker run -p 8000:8000 --env-file .env docpipe
```

Endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check + plugin listing |
| `POST` | `/parse` | Parse a document |
| `POST` | `/extract` | Extract structured data |
| `POST` | `/run` | Parse + extract |
| `POST` | `/ingest` | Ingest into vector DB |
| `POST` | `/search` | Vector similarity search |
| `POST` | `/rag/query` | RAG question answering |
| `POST` | `/evaluate/run` | Evaluate RAG quality |
| `GET` | `/plugins` | List registered plugins |

---

## Docker

```bash
# API server
docker run -p 8000:8000 --env-file .env docpipe

# Parse in container
docker run -v ./data:/data docpipe parse /data/invoice.pdf --format markdown

# Ingest from container
docker run --env-file .env docpipe ingest /data/invoice.pdf \
    --db "postgresql://user:pass@mydb.example.com:5432/mydb" \
    --table invoices \
    --embedding-provider openai --embedding-model text-embedding-3-small
```

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
| **Parsing** | Docling (PDF, DOCX, XLSX, PPTX, HTML, images, audio, video) |
| **Extraction** | LangExtract (Google), LangChain `with_structured_output` |
| **Embeddings** | OpenAI, Google Gemini, Ollama, HuggingFace |
| **Vector store** | PostgreSQL + pgvector |
| **LLM (RAG)** | OpenAI, Google Gemini, Ollama, Anthropic |
| **Reranking** | FlashRank (local), Cohere |

---

## License

MIT — see [LICENSE](LICENSE).
