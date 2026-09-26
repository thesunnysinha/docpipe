# Qdrant vector-store plugin

Install only when selected: `pip install 'docpipe-sdk[qdrant]'`. The base package and curated deployment profiles do not install Qdrant. The adapter uses the public vector facets and requires no Qdrant-specific ingestion, RAG, or search branches.

Example `vector_store` envelope:

```json
{"provider":"qdrant","options":{"url":"https://vectors.example:6333","collection":"documents","api_key_ref":{"kind":"environment","name":"QDRANT_API_KEY"}}}
```

Set `QDRANT_API_KEY` in the process environment. The factory resolves the reference after provider selection; raw `api_key` option values are rejected. For a trusted local server, use an `http://` URL with `allow_insecure_http: true`. For tests only, `location: ":memory:"` uses the client’s local mode. The URL cannot contain credentials, a query, or a fragment.

The adapter supports deterministic UUID point IDs, dense search, metadata equality/range/boolean filters, exact delete-by-source, source aggregation, collection administration, and health. It waits for write/delete completion. A non-completed upsert is reported as uncertain, not success. Source aggregation scans payload pages up to `max_scan_points` (default 100,000) and fails rather than return a partial count. The delete count is a pre-delete snapshot; concurrent writes can affect it.

`timeout_seconds`, `distance` (`cosine`, `dot`, `euclid`), and `max_scan_points` are optional typed settings. Qdrant server authentication, TLS policy, and collection retention remain operator responsibilities. See [security](security.md) and the [vector capability matrix](vectorstores.md).
