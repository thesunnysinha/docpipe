"""Thin httpx client mirroring the docpipe REST API."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

try:
    import httpx
except ImportError as err:  # pragma: no cover
    raise ImportError(
        "docpipe HTTP client requires httpx. Install with: pip install 'docpipe-sdk[http]'"
    ) from err


def _inject_correlation_header(request: httpx.Request) -> None:
    from docpipe.observability.request_context import outbound_correlation_headers

    for key, value in outbound_correlation_headers().items():
        request.headers[key] = value


class DocpipeClient:
    """Synchronous client for the Docpipe REST API.

    This optional client owns an :class:`httpx.Client`, sends JSON request
    bodies for API operations, and configures HTTP Basic Auth on every request.
    It also copies the current Docpipe request/correlation context into
    outbound headers when one is bound. Use it as a context manager or close
    it explicitly to release pooled connections. The client does not retry
    requests or translate HTTP status errors.

    Args:
        base_url: Docpipe server origin or API base path, with or without a
            trailing slash.
        username: Basic Auth username. Defaults to ``"admin"``.
        password: Basic Auth password. Defaults to the empty string; configure
            a real secret when the server requires authentication.
        timeout: Per-request timeout in seconds, passed to HTTPX.

    Raises:
        ValueError: If HTTPX rejects a client option such as the timeout.

    Security:
        Use HTTPS outside trusted local networks. Request payloads may include
        database credentials, model prompts, or other sensitive data; avoid
        logging them and use a secret manager for credentials.
    """

    def __init__(
        self,
        base_url: str,
        *,
        username: str = "admin",
        password: str = "",
        timeout: float = 120.0,
    ) -> None:
        """Create an authenticated session for the supplied Docpipe server.

        The timeout is applied per request. A request-context event hook adds
        correlation headers without changing the caller's payload.
        """
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            auth=(username, password),
            timeout=timeout,
            event_hooks={"request": [_inject_correlation_header]},
        )

    def close(self) -> None:
        """Close the HTTPX session and release its pooled connections.

        Do not issue further requests through this client after closing it.
        """
        self._client.close()

    def __enter__(self) -> DocpipeClient:
        """Return this client for use in a ``with`` block."""
        return self

    def __exit__(self, *args: object) -> None:
        """Close the session when leaving a ``with`` block, including on error."""
        self.close()

    def health(self) -> dict[str, Any]:
        """Fetch the server's health and dependency status.

        Returns:
            Decoded JSON health response from ``GET /health``.

        Raises:
            httpx.HTTPStatusError: If the endpoint returns a non-success status.
            httpx.RequestError: If the request cannot be completed.
            ValueError: If the response body is not valid JSON.
        """
        resp = self._client.get("/health")
        resp.raise_for_status()
        return resp.json()

    def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Submit a JSON request to the document-ingestion endpoint.

        Args:
            payload: API request fields, including source and vector-store
                configuration. Treat credentials in the payload as secrets.

        Returns:
            Decoded JSON ingestion result.

        Raises:
            httpx.HTTPStatusError: If the server rejects the request or returns
                another non-success status.
            httpx.RequestError: If the request cannot be completed.
            ValueError: If the response body is not valid JSON.

        Side effects:
            The server may read the specified source and write parsed vectors
            to the configured store.
        """
        resp = self._client.post("/ingest", json=payload)
        resp.raise_for_status()
        return resp.json()

    def delete_ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Delete ingested records selected by a JSON request body.

        Args:
            payload: API deletion criteria, commonly the collection and source
                identifier whose records should be removed.

        Returns:
            Decoded JSON deletion result, including server-side accounting when
            provided.

        Raises:
            httpx.HTTPStatusError: If the server rejects the request or returns
                another non-success status.
            httpx.RequestError: If the request cannot be completed.
            ValueError: If the response body is not valid JSON.

        Side effects:
            Permanently removes matching records from the server's vector store.
        """
        resp = self._client.request("DELETE", "/ingest", json=payload)
        resp.raise_for_status()
        return resp.json()

    def rag_query(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run a non-streaming RAG request.

        Args:
            payload: API query and retrieval/generation configuration. Avoid
                putting secrets in fields that may be logged by the caller.

        Returns:
            Decoded JSON answer, retrieval metadata, and any other fields
            returned by the endpoint.

        Raises:
            httpx.HTTPStatusError: If the server rejects the query or returns
                another non-success status.
            httpx.RequestError: If the request cannot be completed.
            ValueError: If the response body is not valid JSON.

        Side effects:
            The server may read from the vector store and invoke a language
            model for answer generation.
        """
        resp = self._client.post("/rag/query", json=payload)
        resp.raise_for_status()
        return resp.json()

    def transcribe(
        self,
        file_path: str,
        *,
        backend: str | None = None,
        output_format: str = "plain",
        hotwords: list[str] | None = None,
        api_key: str | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Upload an audio file and return its transcription result.

        Args:
            file_path: Path to a readable local audio file. The client opens
                and closes this file during the request.
            backend: Optional transcription backend selected by the server.
            output_format: Requested result format, such as ``"plain"``.
            hotwords: Optional words sent as a comma-separated form value.
            api_key: Optional provider key sent as a multipart form value. Use
                HTTPS and do not log this argument.
            language: Optional language hint for transcription.

        Returns:
            Decoded JSON transcription response.

        Raises:
            FileNotFoundError: If ``file_path`` does not exist.
            PermissionError: If the file cannot be read.
            httpx.HTTPStatusError: If the server rejects the upload or returns
                another non-success status.
            httpx.RequestError: If the request cannot be completed.
            ValueError: If the response body is not valid JSON.

        Side effects:
            Uploads the file contents and optional provider key to the server.
        """
        import os

        filename = os.path.basename(file_path)
        data: dict[str, str] = {"output_format": output_format}
        if backend:
            data["backend"] = backend
        if hotwords:
            data["hotwords"] = ",".join(hotwords)
        if api_key:
            data["api_key"] = api_key
        if language:
            data["language"] = language
        with open(file_path, "rb") as audio_file:
            resp = self._client.post(
                "/transcribe",
                files={"file": (filename, audio_file)},
                data=data,
            )
        resp.raise_for_status()
        return resp.json()

    def rag_stream(self, payload: dict[str, Any]) -> Iterator[str]:
        """Yield answer chunks from the server's RAG event stream.

        Args:
            payload: API query and retrieval/generation configuration.

        Yields:
            Text chunks from data events. Metadata events are consumed but not
            yielded; the ``[DONE]`` sentinel ends iteration.

        Raises:
            httpx.HTTPStatusError: If the server returns a non-success status
                before streaming begins.
            httpx.RequestError: If the streaming request or response read fails.
            RuntimeError: If the server emits an SSE event named ``error``.

        Resource ownership:
            The response remains open while iterating and is closed when the
            iterator is exhausted, raises, or is explicitly closed. Consumers
            that stop early should call ``close()`` on the iterator (or exhaust
            it) so the connection is returned to the pool.
        """
        with self._client.stream("POST", "/rag/stream", json=payload) as resp:
            resp.raise_for_status()
            event_name = None
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("event:"):
                    event_name = line.split(":", 1)[1].strip()
                    continue
                if line.startswith("data:"):
                    data = line.split(":", 1)[1].strip()
                    if data == "[DONE]":
                        break
                    if event_name == "metadata":
                        event_name = None
                        continue
                    if event_name == "error":
                        raise RuntimeError(data)
                    event_name = None
                    yield data
