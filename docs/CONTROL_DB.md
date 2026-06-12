# Control-plane database (optional)

docpipe is used by many projects (Delegate, Jingo, Andocs, custom apps). **Document vectors and chunks always go to the database you pass on each `/ingest` request** — docpipe does not own your RAG data unless you point it there.

The **control-plane database** is a separate, optional SQLite/Postgres store for operator metadata only:

| Table | Purpose | Opt-in env |
|-------|---------|------------|
| `admin_users` | Seeded admin login | `DOCPIPE_CONTROL_DB_ENABLED=true` |
| `audit_events` | Plugin denials / resolutions | `DOCPIPE_PERSIST_AUDIT_EVENTS=true` |
| `ingest_jobs` | Ingest job metadata (no content) | `DOCPIPE_PERSIST_INGEST_JOBS=true` |

## Docker (SQLite default)

```yaml
environment:
  DOCPIPE_CONTROL_DB_ENABLED: "true"
  DOCPIPE_CONTROL_DB_PATH: /data/docpipe.db
  DOCPIPE_PERSIST_AUDIT_EVENTS: "true"
  DOCPIPE_PERSIST_INGEST_JOBS: "false"
  DOCPIPE_ADMIN_USERNAME: admin
  DOCPIPE_ADMIN_PASSWORD: change-me
```

Mount `./data:/data` so the SQLite file survives restarts. Alembic runs on startup when `DOCPIPE_CONTROL_DB_AUTO_MIGRATE=true` (default).

## Admin panel

When enabled, open `GET /admin` (Basic Auth). Sub-pages:

- `/admin/audit` — persisted audit events
- `/admin/jobs` — ingest job history

## Environment reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCPIPE_CONTROL_DB_ENABLED` | `false` | Enable control-plane DB |
| `DOCPIPE_CONTROL_DB_URL` | — | Full SQLAlchemy URL (overrides SQLite path) |
| `DOCPIPE_CONTROL_DB_PATH` | `/data/docpipe.db` | SQLite file when URL unset |
| `DOCPIPE_CONTROL_DB_AUTO_MIGRATE` | `true` | Run Alembic on startup |
| `DOCPIPE_ADMIN_PANEL_ENABLED` | `true` | Serve `/admin` UI |
| `DOCPIPE_PERSIST_AUDIT_EVENTS` | `false` | Store audit rows |
| `DOCPIPE_PERSIST_PLUGIN_RESOLUTIONS` | `false` | Store plugin resolve events |
| `DOCPIPE_PERSIST_INGEST_JOBS` | `false` | Store ingest metadata |
| `DOCPIPE_ADMIN_USERNAME` | — | Seed user (falls back to `DOCPIPE_USERNAME`) |
| `DOCPIPE_ADMIN_PASSWORD` | — | Seed password (falls back to `DOCPIPE_PASSWORD`) |
| `DOCPIPE_ADMIN_EMAIL` | `admin@localhost` | Seed email |

## Manual migrations

```bash
alembic upgrade head
```

Set `sqlalchemy.url` in `alembic.ini` or pass via env before running.
