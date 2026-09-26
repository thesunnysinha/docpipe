# Hosted MCP server

Docpipe can expose selected document operations to MCP-compatible AI clients
over authenticated Streamable HTTP. The server is opt-in and reuses the same
Docpipe runtime, parser policy, RAG configuration, logging, and lifecycle as the
REST API.

## Install and enable

Install the optional server dependency alongside the Docpipe API:

```bash
pip install 'docpipe-sdk[server,mcp-server]'
```

Provide secrets through the deployment's secret manager or Kubernetes Secret.
Do not put bearer values in a committed `.env`, container image, or manifest.

```dotenv
DOCPIPE_MCP_SERVER_ENABLED=true
DOCPIPE_MCP_OPERATOR_TOKENS=["<one-or-more-random-tokens-of-at-least-32-characters>"]
DOCPIPE_MCP_ALLOWED_HOSTS=["docpipe.example.com"]
DOCPIPE_MCP_ALLOWED_ORIGINS=[]
DOCPIPE_MCP_TOOL_TIMEOUT_SECONDS=300
DOCPIPE_MCP_RATE_LIMIT_PER_MINUTE=60
```

Generate high-entropy tokens with a secret manager or a cryptographic random
generator. Multiple tokens can be active during rotation; revoke a token by
removing it from the configured list and restarting/redeploying the service.
FastMCP stores only SHA-256 token digests for validation, and comparisons are
constant-time. Use HTTPS at the ingress and keep operator tokens out of logs.

`DOCPIPE_MCP_ALLOWED_HOSTS` must contain exact host values accepted by the
transport, such as `docpipe.example.com` (include a port only when clients
actually send it). Wildcards are rejected. `DOCPIPE_MCP_ALLOWED_ORIGINS` is
usually empty for server-to-server clients; configure exact browser origins only
if browser-based MCP clients need CORS. Forward the public host consistently
through the ingress so Host validation sees an allowed value.

The MCP endpoint is `https://docpipe.example.com/mcp`. It uses stateless
Streamable HTTP and requires:

```http
Authorization: Bearer <operator-token>
```

The separate `/mcp/health` endpoint returns liveness only and does not expose
configuration. Docpipe's existing `/mcp/tools` and `/mcp/call` routes remain
available for compatibility; clients implementing MCP should use `/mcp`.

## Tools and boundaries

- `docpipe_parse` parses a source accepted by the operator-configured source
  policy. Private and loopback URL access remains governed by the Docpipe SSRF
  policy, and local paths remain limited by configured source roots.
- `docpipe_rag_query` queries the operator-configured vector index and model
  settings. It does not accept a database connection string or model API key
  from the MCP client.

If Docpipe tenant identity mapping or plugin tenant policies are enabled, set
`DOCPIPE_MCP_TENANT_ID` to the operator-assigned tenant for these shared MCP
operator tokens. Startup fails closed when that scope is missing. Current MCP
tokens share this configured tenant; per-token tenant assignment is not yet
supported. Without tenant policies, the MCP server uses the operator's default
plugin policy and vector configuration.

## Client compatibility

Any MCP host that can attach a static `Authorization: Bearer` token can connect.
Authentication settings vary by client: Claude's hosted custom-connector UI
documents OAuth setup rather than a generic pasted bearer token, while its
Managed Agents connector supports static bearer credentials. For a client that
requires OAuth, place an OAuth-capable gateway in front of Docpipe or add a
Docpipe OAuth provider; do not disable MCP authentication to work around the
client limitation.

## Operational notes

The endpoint shares the API process and resource limits. Scale it by scaling the
Docpipe deployment and its underlying shared services; keep parser concurrency,
provider rate limits, ingress request limits, MCP's pre-auth request limit, and
tool timeouts aligned with capacity. MCP POST traffic is bounded per transport
peer by `DOCPIPE_MCP_RATE_LIMIT_PER_MINUTE` before authentication and before
request-body processing. Parsing and RAG operations may be expensive, so issue
narrowly scoped tokens only to trusted integrations. MCP token authentication
is independent of Docpipe's HTTP Basic API authentication.

The standalone FastMCP package is optional. When the endpoint is enabled but the
extra, tokens, or host allowlist are missing, application startup fails with a
configuration error instead of exposing an unauthenticated endpoint.
