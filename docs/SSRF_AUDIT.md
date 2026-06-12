# Parser SSRF audit (2026-06-12)

Part of docpipe's **internal security** surface. Perimeter exposure, TLS, and auth setup are deployer responsibilities — see [`INTERNAL_SECURITY.md`](INTERNAL_SECURITY.md).

## Threat

HTTP(S) `source` values on `/parse`, `/ingest`, and `/run` can be abused for server-side request forgery against internal services **when docpipe can reach those addresses** (e.g. `DOCPIPE_ALLOW_PRIVATE_URLS=true` on a cluster network).

## Controls

| Parser | URL handling | Guard |
|--------|----------------|-------|
| markitdown | `convert()` / pre-fetch | Inline private-IP check in `markitdown_parser.py`; `DOCPIPE_ALLOW_PRIVATE_URLS` |
| docling | native URL fetch | Docling private-IP rejection + `DOCPIPE_ALLOW_PRIVATE_URLS` |
| mineru | `path_list` may include URLs | `assert_safe_http_source` before `do_parse` |
| paddleocr | `predict(source)` | `assert_safe_http_source` |
| unstructured | `partition(filename=...)` | `assert_safe_http_source` |
| glm-ocr | `run(source)` | `assert_safe_http_source` |
| pymupdf | local paths only | N/A |

Shared helper: `src/docpipe/parsers/url_safety.py`.

## Operator guidance

- **Public deployments:** keep `DOCPIPE_ALLOW_PRIVATE_URLS=false` (default).
- **Docker Compose / internal MinIO:** set `DOCPIPE_ALLOW_PRIVATE_URLS=true` only on trusted networks.
- Prefer signed, time-limited URLs over raw internal hostnames when possible.
