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
    """Sync HTTP client for docpipe (Basic Auth, JSON bodies)."""

    def __init__(
        self,
        base_url: str,
        *,
        username: str = "admin",
        password: str = "docpipe",
        timeout: float = 120.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            auth=(username, password),
            timeout=timeout,
            event_hooks={"request": [_inject_correlation_header]},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> DocpipeClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def health(self) -> dict[str, Any]:
        resp = self._client.get("/health")
        resp.raise_for_status()
        return resp.json()

    def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.post("/ingest", json=payload)
        resp.raise_for_status()
        return resp.json()

    def delete_ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.request("DELETE", "/ingest", json=payload)
        resp.raise_for_status()
        return resp.json()

    def rag_query(self, payload: dict[str, Any]) -> dict[str, Any]:
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
        """POST /transcribe — speech-to-text (OpenAI Whisper or VibeVoice)."""
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
        """Yield answer tokens; skips SSE metadata events."""
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
