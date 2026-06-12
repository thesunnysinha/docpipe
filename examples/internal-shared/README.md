# Internal shared docpipe

Single docpipe instance for multiple internal apps. **No Postgres in this stack** — each client passes `connection_string` and `table_name` on every ingest/RAG call.

## Start

```bash
cp .env.example .env
# Set OPENAI_API_KEY and DOCPIPE_PASSWORD
docker compose up -d
```

- API: http://localhost:8000
- Admin: http://localhost:8000/admin (Basic Auth)
- Docs: http://localhost:8000/docs

## Volumes

| Mount | Purpose |
|-------|---------|
| `./data` | Control-plane SQLite (`docpipe.db`), model cache |
| `./uploads` | Optional read-only docs at `/data/uploads` for `file:///data/uploads/...` sources |

## When to use

- Kubernetes `ClusterIP` docpipe shared by Delegate, Jingo, Andocs
- VPN-only internal network
- You already have per-app Postgres with pgvector

Full configuration reference: [examples/README.md](../README.md)
