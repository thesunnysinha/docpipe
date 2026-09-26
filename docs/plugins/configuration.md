# Plugin configuration

The namespaced HTTP envelope has a stable shape:

```json
{"vector_store":{"provider":"pgvector","options":{"collection":"documents","dsn":"postgresql://host/db"}}}
```

`source_plugin` uses the same `provider`/`options` structure for ingest requests. Provider names are catalog keys, not Python classes. The shared envelope accepts only JSON-safe values. The selected factory validates exact provider-specific keys after policy checks and reports a nested option path when invalid.

Process defaults can use `DOCPIPE_VECTOR_STORE` as JSON and `DOCPIPE_SOURCE_PLUGIN_OPTIONS` as JSON keyed by source scheme. `DOCPIPE_ENABLED_SOURCES`, `DOCPIPE_ENABLED_VECTORSTORES`, and `DOCPIPE_DISABLED_PLUGINS` narrow process policy. Tenant allowlists may further narrow it, but cannot override a process denial. Configure `DOCPIPE_TENANT_PLUGIN_POLICIES` as a JSON object keyed by tenant ID, and `DOCPIPE_TENANT_IDENTITY_MAP` as a JSON object mapping authenticated Basic Auth usernames to those IDs. The caller-provided `X-Docpipe-Tenant-Id` header is ignored. If tenant policies are configured but a verified username has no mapping, the request is denied; do not share one Basic Auth account across tenants if tenant isolation is required.

Legacy `vector_backend`, `connection_string`, `turbovec_index_dir`, and `turbovec_bit_width` remain accepted. Agreeing old and new values are accepted; explicit conflicts fail with the legacy field name. New values take precedence when old values were implicit defaults. Source defaults map similarly, while request-supplied local/HTTP limits cannot relax operator security policy.

Secret references are transported unresolved. Never place a raw credential in discovery metadata or logs. Provider factories resolve references through `CredentialResolver` only after selection. See [the migration guide](../migrations/plugin-configuration.md).
