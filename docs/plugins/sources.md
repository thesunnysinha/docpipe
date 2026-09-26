# Source resolver plugins

The URI scheme selects a registered resolver: local paths and `file://` use `local`, HTTP(S) uses `http`, and additional schemes can be supplied by plugins. A request may pass a matching `source_plugin` envelope; process defaults use `DOCPIPE_SOURCE_PLUGIN_OPTIONS` keyed by provider.

| Resolver | Extra | Streaming | Materialization | Security boundary |
| --- | --- | --- | --- | --- |
| Local | Base | Yes | Yes | Allowed roots, symlink/traversal checks, size limits. |
| HTTP(S) | `docpipe-sdk[http]` | Yes | Yes | SSRF/DNS pinning, redirect checks, deadlines, byte limits. |
| S3/MinIO | `docpipe-sdk[s3]` | Yes | Yes | Operator-owned bucket/prefix, endpoint, credential, and object-size policy. |

`ResolvedSourceHandle` owns its stream and any temporary artifact. Parsing must occur inside its async context; after exit, opening or materializing fails. Handles preserve source identity in descriptors even when a legacy parser receives a temporary local path. Content fingerprints should be streamed, not computed by reading an entire object into memory.

Built-in local and HTTP security limits are operator-owned. Request options cannot widen them. A custom resolver must enforce equivalent boundaries appropriate to its transport. See [security](security.md).

Local-path ingestion is disabled by default. Set `DOCPIPE_SOURCE_ALLOWED_ROOTS` to a JSON array of existing, narrowly scoped directories (for example `DOCPIPE_SOURCE_ALLOWED_ROOTS='["/data/documents"]'`). Do not grant the application its working directory or secret/configuration mounts unless callers genuinely need them.

S3/MinIO is optional. Configure allowed buckets and a private temporary directory in process settings before selecting it from a request. See [the S3 guide](s3.md).
