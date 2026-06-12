# Internal security model

docpipe is an **open-source library and API server**. Deployers are responsible for how it is exposed: network placement, TLS, ingress, secrets, identity providers, and whether the service is reachable from the public internet.

This document covers **in-process and shared-internal concerns** — what docpipe does inside the boundary you draw, especially the pattern where one docpipe instance serves multiple internal apps (Delegate, Jingo, Andocs) on a trusted cluster network.

---

## Out of scope (deployer responsibility)

| Topic | Notes |
|-------|--------|
| Public exposure | Do not put an unauthenticated instance on the internet. Use a private network, mesh, or API gateway. |
| TLS / mTLS | Terminate TLS at ingress or sidecar; docpipe serves plain HTTP by default. |
| Strong credentials | Change `DOCPIPE_PASSWORD` / seed admin password; use K8s Secrets or your secret manager. |
| Identity federation | HTTP Basic Auth is built in; map OIDC/JWT at your gateway if you need SSO. |
| Provider API keys | `OPENAI_API_KEY`, etc. are operator env vars — protect like any other secret. |
| `/metrics` without auth | Standard Prometheus scrape pattern; restrict network access to the metrics port/path. |
| Per-app Postgres ACLs | Each app should use its own DB role; docpipe only connects with credentials you pass per request. |

---

## In scope (what docpipe enforces internally)

### 1. RAG data stays in the caller's database

Vector chunks and embeddings are written to the **`connection_string` + `table_name` on each `/ingest` and `/rag/*` request**. docpipe does not merge collections across apps unless callers point at the same database.

The optional **control-plane DB** stores operator metadata only (admin login, optional audit/job rows). It does **not** store document text or embeddings unless you misconfigure persistence flags expecting content (they store metadata only).

### 2. Plugin guardrails (operator + optional per-tenant)

Operators constrain which parsers, chunkers, and rerankers can run:

```bash
DOCPIPE_ENABLED_PARSERS=markitdown,docling
DOCPIPE_DISABLED_PLUGINS=pymupdf,mineru
DOCPIPE_TENANT_PLUGIN_POLICIES='{"delegate":{"enabled_parsers":"markitdown,docling"},"jingo":{"enabled_parsers":"docling,glm-ocr"}}'
```

Denied plugins return HTTP errors and can be logged when `DOCPIPE_PERSIST_AUDIT_EVENTS=true`. See `src/docpipe/profiles/guardrails.py`.

### 3. `X-Docpipe-Tenant-Id` is a hint, not proof of identity

The header selects a row in `DOCPIPE_TENANT_PLUGIN_POLICIES`. **Any authenticated client can send any tenant id.**

For strict internal multi-team isolation, bind tenant at your **gateway or calling service** (e.g. Delegate always sends `X-Docpipe-Tenant-Id: delegate` from server-side code, never from the mobile client). docpipe does not issue tenant tokens.

### 4. URL sources and SSRF on internal networks

HTTP(S) `source` values can trigger server-side fetches. Controls:

- Default: private/loopback targets are **rejected** (`DOCPIPE_ALLOW_PRIVATE_URLS=false`).
- Internal MinIO / presigned URLs: set `DOCPIPE_ALLOW_PRIVATE_URLS=true` **only on networks you trust** (Docker Compose, cluster-internal Service).

Parser coverage: see [`SSRF_AUDIT.md`](SSRF_AUDIT.md). Prefer time-limited presigned URLs over raw internal hostnames.

### 5. Local and mounted file paths

`source` may be a path or `file://` URL readable by the docpipe process. Any caller with API access can request parse/ingest of files under mounted volumes (e.g. `/data/uploads/...`).

**Mitigation:** mount only intended directories; do not mount host `/` or sensitive paths; treat API credentials as filesystem access to those mounts.

### 6. Rate limiting (intra-cluster abuse)

`DOCPIPE_RATE_LIMIT_ENABLED` applies per-preset limits on expensive POST routes (`/ingest`, `/parse`, `/rag/*`). Keyed by Basic Auth identity + optional tenant header — useful when many internal services share one docpipe.

### 7. Audit trail (optional)

When control DB + `DOCPIPE_PERSIST_AUDIT_EVENTS=true`:

- Plugin denials and `/plugins/resolve` decisions can be persisted.
- View at `GET /admin/audit` (Basic Auth).

Useful for compliance and debugging policy mistakes, not a substitute for network ACLs.

### 8. Control-plane credentials

Admin passwords in the control DB use **scrypt** hashing (`src/docpipe/db/security.py`). Seed user is created on first boot from `DOCPIPE_ADMIN_*` or `DOCPIPE_USERNAME` / `DOCPIPE_PASSWORD`.

---

## Recommended internal shared API setup

From [`examples/internal-shared/`](../examples/internal-shared/) and [`examples/README.md`](../examples/README.md):

```bash
DOCPIPE_CONTROL_DB_ENABLED=true
DOCPIPE_PERSIST_AUDIT_EVENTS=true
DOCPIPE_ALLOW_PRIVATE_URLS=true          # only on trusted internal network
DOCPIPE_PASSWORD=<strong-secret>       # deployer sets this
DOCPIPE_ENABLED_PARSERS=markitdown,docling   # optional tighten
```

Each downstream app:

- Calls docpipe over cluster DNS (`http://docpipe:8000`).
- Passes **its own** `connection_string` on every ingest/RAG call.
- Sets `X-Docpipe-Tenant-Id` from **server-side** code if using tenant policies.
- Never forwards docpipe credentials to end-user clients.

---

## Summary

| Layer | Who handles it |
|-------|----------------|
| Firewall, TLS, SSO, secret rotation | Deployer |
| Which plugins can run, audit log, rate limits, URL fetch policy | docpipe (configured by operator) |
| Where vectors live | Calling app (`connection_string` per request) |
| Tenant plugin policy selection | Calling app (trusted header) + operator JSON policy |

For URL parser details: [`SSRF_AUDIT.md`](SSRF_AUDIT.md). For control DB: [`CONTROL_DB.md`](CONTROL_DB.md).
