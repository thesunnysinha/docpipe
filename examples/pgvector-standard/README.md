# pgvector standard stack

docpipe API + Postgres 16 with pgvector. Good for **local development** when you want a single vector DB on `localhost:5432`.

## Start

```bash
cp .env.example .env
docker compose up -d
curl -u admin:docpipe http://localhost:8000/health
```

Default ingest target: `postgresql://docpipe:docpipe@db:5432/docpipe` (from inside compose) or `@localhost:5432` from the host.

See [examples/README.md](../README.md) for all environment variables.
