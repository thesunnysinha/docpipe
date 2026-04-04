# docpipe

Unified document parsing, structured extraction, and vector ingestion pipeline.

## Overview

docpipe connects document parsing (Docling), LLM-based structured extraction (LangExtract + LangChain), and vector ingestion (pgvector via LangChain) into a single composable pipeline.

**Three independent pipelines, composable together:**

1. **Parse**: Unstructured docs → parsed text/markdown (Docling)
2. **Extract**: Text → structured entities via LLM (LangExtract or LangChain)
3. **Ingest**: Parsed chunks → embeddings → your vector DB (LangChain + pgvector)

## Install

```bash
# Core only
pip install docpipe

# With all backends
pip install "docpipe[all]"

# Pick what you need
pip install "docpipe[docling]"              # Document parsing
pip install "docpipe[langextract]"          # Google LangExtract
pip install "docpipe[openai]"              # OpenAI embeddings + LLM
pip install "docpipe[pgvector]"            # PostgreSQL vector store
pip install "docpipe[server]"              # FastAPI server
```

## Quick Start

### Python API

```python
import docpipe

# Parse a document
doc = docpipe.parse("invoice.pdf")
print(doc.markdown)

# Extract structured data
schema = docpipe.ExtractionSchema(
    description="Extract invoice line items with amounts",
    model_id="gemini-2.5-flash",
)
results = docpipe.extract(doc.text, schema)

# Full pipeline
result = docpipe.run("invoice.pdf", schema)

# Ingest into your vector DB
config = docpipe.IngestionConfig(
    connection_string="postgresql://user:pass@localhost:5432/mydb",
    table_name="invoices",
    embedding_provider="openai",
    embedding_model="text-embedding-3-small",
)
docpipe.ingest("invoice.pdf", config=config)
```

### CLI

```bash
docpipe parse invoice.pdf --format markdown
docpipe extract "John Doe, age 30" --schema schema.yaml --model gemini-2.5-flash
docpipe run invoice.pdf --schema schema.yaml --model gemini-2.5-flash
docpipe ingest invoice.pdf --db "postgresql://..." --table invoices \
    --embedding-provider openai --embedding-model text-embedding-3-small
docpipe search "total amount" --db "postgresql://..." --table invoices \
    --embedding-provider openai --embedding-model text-embedding-3-small
docpipe serve
docpipe plugins list
```

### Docker

```bash
# API server
docker run -p 8000:8000 --env-file .env docpipe

# CLI
docker run -v ./data:/data docpipe parse /data/invoice.pdf
```

## Plugin System

Third-party packages can register as plugins via entry points:

```toml
# In your package's pyproject.toml
[project.entry-points."docpipe.parsers"]
my_parser = "my_package:MyParser"

[project.entry-points."docpipe.extractors"]
my_extractor = "my_package:MyExtractor"
```

## License

MIT
