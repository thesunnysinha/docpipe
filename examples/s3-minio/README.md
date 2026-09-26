# Local S3-compatible test service

Set throwaway `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY` environment variables, then run `docker compose up -d` in this directory. This example runs SeaweedFS and binds its S3 endpoint on port 8333 to loopback only. Create a test bucket such as `reports` and a private artifact directory before using the S3 plugin. Configure `endpoint_url` as `http://localhost:8333`, `allow_insecure_http` as `true`, and the credential references in [the S3 guide](../../docs/plugins/s3.md). Do not reuse these test credentials or the HTTP override in production.

The CI integration test creates and removes its own test bucket in an ephemeral SeaweedFS container. Stop this example with `docker compose down`.
