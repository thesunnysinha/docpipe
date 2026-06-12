# turbovec local

docpipe with **file-based** vector indices (no Postgres). Indices live under `./data/indices`.

## Start

```bash
cp .env.example .env
docker compose up -d
```

## Ingest example

```bash
curl -u admin:docpipe -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "/path/to/doc.pdf",
    "connection_string": "postgresql://unused/local",
    "table_name": "my_collection",
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "vector_backend": "turbovec",
    "turbovec_index_dir": "/data/indices"
  }'
```

Note: `connection_string` is still required by the API schema for pgvector compatibility; turbovec uses `turbovec_index_dir` + `table_name` for storage.

Requires `docpipe-sdk[turbovec]` in the image — use `balanced` or custom build with turbovec extra.

See [examples/README.md](../README.md).
