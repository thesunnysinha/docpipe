"""HTTP client helpers for apps integrating with docpipe (Delegate, Jingo, Andocs)."""

from __future__ import annotations

from typing import Any

import httpx


class DocpipeClient:
    """Minimal typed client for plugin discovery and preset-based ingest/RAG."""

    def __init__(
        self,
        base_url: str,
        *,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        auth = (username, password) if username and password else None
        self._client = httpx.Client(base_url=self._base_url, auth=auth, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> DocpipeClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def plugins(self) -> dict[str, Any]:
        response = self._client.get("/plugins")
        response.raise_for_status()
        return response.json()

    def profiles(self) -> dict[str, Any]:
        response = self._client.get("/profiles")
        response.raise_for_status()
        return response.json()

    def resolve(
        self,
        *,
        source: str | None = None,
        goal: str = "ingest",
        preset: str | None = None,
    ) -> dict[str, Any]:
        response = self._client.post(
            "/plugins/resolve",
            json={"source": source, "goal": goal, "preset": preset},
        )
        response.raise_for_status()
        return response.json()

    def available_preset_names(self) -> list[str]:
        data = self.profiles()
        return list(data.get("runtime_presets", {}).keys())

    def ingest(
        self,
        *,
        source: str,
        connection_string: str,
        table_name: str,
        embedding_provider: str,
        embedding_model: str,
        preset: str | None = "balanced",
        **kwargs: Any,
    ) -> dict[str, Any]:
        body = {
            "source": source,
            "connection_string": connection_string,
            "table_name": table_name,
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_model,
            "preset": preset,
            **kwargs,
        }
        response = self._client.post("/ingest", json=body)
        response.raise_for_status()
        return response.json()

    def rag_query(
        self,
        *,
        question: str,
        connection_string: str,
        table_name: str,
        embedding_provider: str,
        embedding_model: str,
        llm_provider: str,
        llm_model: str,
        system_prompt: str,
        preset: str | None = "balanced",
        **kwargs: Any,
    ) -> dict[str, Any]:
        body = {
            "question": question,
            "connection_string": connection_string,
            "table_name": table_name,
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_model,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "system_prompt": system_prompt,
            "preset": preset,
            **kwargs,
        }
        response = self._client.post("/rag/query", json=body)
        response.raise_for_status()
        return response.json()
