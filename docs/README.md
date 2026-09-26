# Documentation map

This directory is the source of truth for operational and engineering guidance
that ships with Docpipe. The website presents a reader-friendly view of these
guides; when behavior changes, update the relevant source guide first and then
sync the corresponding website section.

## Use Docpipe

- [Integration guide](INTEGRATION.md) — shared API setup, client integration,
  deployment examples, and runtime presets.
- [Hosted MCP server](MCP_SERVER.md) — optional MCP installation, bearer-token
  authentication, tenant boundaries, and transport operations.
- [RAG response cache](RAG_CACHE.md) — Redis and in-process backends, cache
  isolation, sensitive-data handling, and failure behavior.
- [LightRAG integration](LIGHTRAG.md) — optional graph synchronization.
- [Control-plane database](CONTROL_DB.md) — admin and opt-in operational
  metadata storage, distinct from customer vector data.

## Configure plugins

- [Plugin architecture](architecture/plugins.md) — provider discovery,
  capabilities, and the extension boundary.
- [Plugin configuration](plugins/configuration.md) — namespaced provider and
  options settings.
- [Compatibility policy](plugins/compatibility.md) — supported API and
  dependency compatibility guarantees.
- [Security model](plugins/security.md) and [source policies](plugins/sources.md)
  — trust boundaries for third-party adapters and document sources.
- [Qdrant vector store](plugins/qdrant.md) and [S3-compatible sources](plugins/s3.md)
  — provider-specific setup and current verification limits.
- [Authoring guide](plugins/authoring.md), [performance notes](plugins/performance.md),
  and [troubleshooting](plugins/troubleshooting.md) — maintainers and adapter
  authors.

## Security and operations

- [Internal security model](INTERNAL_SECURITY.md) — authentication, source
  restrictions, secrets, and production boundaries.
- [SSRF audit](SSRF_AUDIT.md) — URL-fetch protections and verification notes.
- [Integration guide](INTEGRATION.md) — deployment and runtime configuration.

## Architecture and change history

- [Architecture decisions](architecture/decisions/) — accepted design decisions.
- [Dependency boundaries](architecture/dependency-boundaries.md) — optional
  dependency and import boundaries.
- [Migrations](migrations/) — operator-facing upgrade guidance.
- [Plans and specifications](superpowers/) — historical implementation plans;
  these describe intent at the time and are not a statement of current support.

## Keeping documentation reliable

The repository's code, tests, packaged dependency metadata, and deployment
manifests define actual behavior. A guide must not promise support solely
because a plan mentions it or a configuration model accepts a value. Provider
claims should cite or link to a concrete test, CI job, or documented manual
verification. In particular, distinguish an S3-compatible implementation from
conformance with any specific service, and distinguish a buildable profile from
an image that CI actually publishes.
