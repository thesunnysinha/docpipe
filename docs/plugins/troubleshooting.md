# Plugin troubleshooting

- If a plugin appears in `/plugins` but has `allowed: false`, check process deny/allow lists and the tenant policy. A tenant cannot re-enable a process-denied plugin.
- If `available: false` or `compatible: false`, check the installation hint and API version range. Do not assume that an entry point means its optional SDK is installed.
- If a selected factory rejects an option, inspect the nested field path (for example `vector_store.options.collection`) and compare it with that provider's configuration model.
- If `/health` is green but a plugin operation fails, use authenticated `/plugins/health` to probe the configured vector dependency. `/health` intentionally avoids loading optional integrations.
- For HTTP source failures, verify allowed ports and public DNS resolution. Private destinations require explicit operator policy; a request cannot override it.
- For source cleanup failures, inspect safe event codes and opaque handle IDs. Do not enable content or signed-URL logging to debug them.

When reporting an issue, include Docpipe version, plugin name/version, category, safe error code, and selected capability—not credentials, DSNs, source URLs, or document data.
