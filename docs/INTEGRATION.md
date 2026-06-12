# Integrating apps with docpipe (Delegate, Jingo, Andocs)

## Discovery flow

1. Call `GET /profiles` — install profile, runtime presets, server defaults.
2. Call `GET /plugins` — installed plugins with `available`, `allowed`, `tier`, `license`.
3. Optionally `POST /plugins/resolve` — recommendation for a file + goal.
4. Pass `preset` on `/ingest`, `/rag/query`, `/agents/query` or set explicit fields.

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
        connection_string="postgresql://...",
        table_name="assistant_docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        preset="balanced",
    )
```

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
| `profile-balanced` | `:balanced` | **Default** K8s |
| `profile-quality` | `:quality` | OCR + BGE rerank |
| `profile-agents` | `:agents` | AutoGen |

```bash
pip install "docpipe-sdk[profile-balanced]"
docker pull ghcr.io/thesunnysinha/docpipe:balanced
```

## Guardrails

```bash
DOCPIPE_PROFILE=balanced
DOCPIPE_DEFAULT_PARSER=auto
DOCPIPE_DEFAULT_PARSER_TIER=balanced
DOCPIPE_DEFAULT_RUNTIME_PRESET=balanced
DOCPIPE_DISABLED_PLUGINS=pymupdf,mineru
DOCPIPE_ENABLED_PARSERS=markitdown,docling
```
