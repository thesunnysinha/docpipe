# Migrating to namespaced plugin configuration

Existing clients can keep sending `connection_string`, `vector_backend`, and TurboVec fields. They are translated into the same plugin options before the provider factory runs. New clients should send `vector_store: {"provider": "...", "options": {...}}`; ingest may additionally send `source_plugin` matching the source URI scheme.

For pgvector, move `connection_string` to `vector_store.options.dsn` and `table_name` to `vector_store.options.collection`. For TurboVec, move `turbovec_index_dir` to `options.index_root` and `turbovec_bit_width` to `options.bit_width`. Keep `table_name` on the request for response compatibility and make it agree with the collection option. A new provider such as Qdrant does not require a legacy PostgreSQL connection string.

Explicit old/new conflicts fail early with a field-specific configuration error. Omitted old values do not override the namespaced envelope. Legacy field deprecation warnings occur at most once per process per field, not once per document or request.

The legacy request fields remain supported throughout the 1.x line. Removal will occur no earlier than 2.0, after at least two minor releases and six months of documented notice. The namespaced transport shape is additive; provider-specific option keys may evolve with each provider's versioned contract. Track migration progress by monitoring value-free deprecation warnings.
