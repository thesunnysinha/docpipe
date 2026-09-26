# Vector-store plugins

Choose a provider in `vector_store.provider` and pass provider-owned settings in `vector_store.options`. Existing `vector_backend`, `connection_string`, and `turbovec_*` fields are translated for compatibility.

| Provider | Extra | Dense search | Upsert | Delete by source | Health | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| pgvector | `docpipe-sdk[pgvector]` | Yes | Yes | Yes | Yes | PostgreSQL service and DSN required. |
| TurboVec | `docpipe-sdk[turbovec]` | Yes | Yes | Yes | Yes | Local index root. |
| Qdrant | `docpipe-sdk[qdrant]` | Yes | Yes | Yes | Yes | Optional remote or test-local adapter; [details](qdrant.md). |

The public `VectorStoreBinding` advertises independent capabilities. Callers must check capabilities before using a facet. `VectorQuery` and `VectorRecord` contain only normalized Python values. Metadata predicates use the typed `Equals`, `In`, `Range`, `And`, `Or`, and `Not` models, which an adapter compiles to its vendor syntax.

`WriteBatchResult` must account for every requested record as accepted, rejected, or uncertain. Partial and uncertain outcomes are failures for ingestion; they must never be reported as a normal completed write. See [the external example](../../examples/plugin-package/README.md) for a minimal in-memory adapter and [configuration](configuration.md) for request envelopes.
