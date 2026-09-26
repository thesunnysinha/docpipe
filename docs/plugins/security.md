# Plugin security

Treat every plugin as executable code with the host process's privileges. Static discovery is safe to perform on untrusted metadata, but loading a plugin is an explicit trust decision. Use process and tenant allowlists; installation does not imply authorization. Request bodies cannot choose an import path or class.

Third-party plugins are not sandboxed: installed plugin factories execute in-process with Docpipe's filesystem, network, and environment access. Install only trusted distributions and use `DOCPIPE_ENABLED_SOURCES` / `DOCPIPE_ENABLED_VECTORSTORES` to allow the providers the deployment needs. For multi-tenant policies, bind Basic Auth usernames to tenant IDs with `DOCPIPE_TENANT_IDENTITY_MAP`; never select policy from a caller-controlled tenant header.

The built-in expensive-route limiter keys on the TCP peer address by default and never trusts forwarded identity headers from arbitrary peers. If requests arrive through a shared reverse proxy, configure `DOCPIPE_RATE_LIMIT_TRUSTED_PROXY_CIDRS` with only the proxy networks that overwrite or append the connecting client address in `X-Forwarded-For`; the limiter then walks that chain from the trusted peer. Keep per-client rate limits at the ingress as an additional boundary.

Source plugins must enforce allowed roots, buckets, prefixes, endpoint policy, deadlines, and streamed byte limits. HTTP resolution checks each redirect and pins the vetted DNS address at connection time. Signed URLs, headers, credentials, local paths, document content, prompts, and vectors must not enter exception text returned to clients or structured logs.

Credential references are resolved only inside selected factories. Keep secret values out of Pydantic dumps, cache keys, OpenAPI examples, manifests, and telemetry. Plugins should report stable error codes and safe context paths rather than raw vendor exception messages.

Scope ownership is mandatory for network clients and temporary files. Close resources on cancellation as well as success and error. Put optional SDKs only in extras; do not import them from the base package or metadata discovery path.
