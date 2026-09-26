"""HTTP client helpers for apps integrating with docpipe (Delegate, Jingo, Andocs)."""

from __future__ import annotations

from typing import Any

import httpx


class DocpipeClient:
    """Synchronous client for plugin discovery, ingest, and RAG queries.

    The client owns an :class:`httpx.Client` and its connection pool. Use it as
    a context manager or call :meth:`close` when finished. Basic authentication
    is enabled only when both ``username`` and ``password`` are non-empty; when
    either is omitted, requests are sent without authentication. The client
    does not retry requests or transform API errors.

    Args:
        base_url: Docpipe server origin or base path, with or without a trailing
            slash. Endpoint paths are appended to this value.
        username: Optional Basic Auth username. Must be supplied together with
            ``password`` to enable authentication.
        password: Optional Basic Auth password. Must be supplied together with
            ``username`` to enable authentication.
        timeout: Per-request timeout in seconds, passed to HTTPX.

    Raises:
        ValueError: If HTTPX rejects a client option such as the timeout.

    Security:
        Use HTTPS when the server is not on a trusted local network. Ingest
        and RAG requests include the supplied database connection string in
        their JSON bodies; do not log these request bodies or expose them to
        untrusted intermediaries.
    """

    def __init__(
        self,
        base_url: str,
        *,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        """Create the HTTP session used for subsequent API calls.

        See the class documentation for credential handling and transport
        security. The supplied timeout applies to each request rather than to
        the lifetime of the client.
        """
        self._base_url = base_url.rstrip("/")
        auth = (username, password) if username and password else None
        self._client = httpx.Client(base_url=self._base_url, auth=auth, timeout=timeout)

    def close(self) -> None:
        """Close the underlying HTTPX session and release pooled connections.

        The client must not be used for additional requests after it is closed.
        """
        self._client.close()

    def __enter__(self) -> DocpipeClient:
        """Return this client for use in a ``with`` block."""
        return self

    def __exit__(self, *args: object) -> None:
        """Close the session when leaving a ``with`` block, including on error."""
        self.close()

    def plugins(self) -> dict[str, Any]:
        """Fetch the server's plugin catalog.

        Returns:
            Decoded JSON response containing installed plugin information.

        Raises:
            httpx.HTTPStatusError: If the server returns a non-success status.
            httpx.RequestError: If the request cannot be completed.
            ValueError: If the response body is not valid JSON.
        """
        response = self._client.get("/plugins")
        response.raise_for_status()
        return response.json()

    def profiles(self) -> dict[str, Any]:
        """Fetch the available runtime presets and profile metadata.

        Returns:
            Decoded JSON response from ``GET /profiles``.

        Raises:
            httpx.HTTPStatusError: If the server returns a non-success status.
            httpx.RequestError: If the request cannot be completed.
            ValueError: If the response body is not valid JSON.
        """
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
        """Resolve a preset and optional source into runtime plugin choices.

        Args:
            source: Optional URI or source identifier used for source-aware
                plugin selection.
            goal: Resolution goal understood by the server, commonly
                ``"ingest"`` or ``"rag"``.
            preset: Optional named preset; ``None`` delegates selection to the
                server's defaults.

        Returns:
            Decoded JSON resolution response.

        Raises:
            httpx.HTTPStatusError: If the server rejects the resolution request
                or returns another non-success status.
            httpx.RequestError: If the request cannot be completed.
            ValueError: If the response body is not valid JSON.
        """
        response = self._client.post(
            "/plugins/resolve",
            json={"source": source, "goal": goal, "preset": preset},
        )
        response.raise_for_status()
        return response.json()

    def available_preset_names(self) -> list[str]:
        """Return the names of runtime presets advertised by the server.

        This is a convenience projection of :meth:`profiles`; it performs a
        network request each time and returns an empty list if the response
        omits ``runtime_presets``.

        Raises:
            httpx.HTTPStatusError: If the profiles endpoint returns a
                non-success status.
            httpx.RequestError: If the request cannot be completed.
            ValueError: If the response body is not valid JSON.
        """
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
        """Submit a document source for parsing, chunking, and vector ingestion.

        Args:
            source: Source URI or identifier accepted by the server.
            connection_string: Database connection string used by the vector
                store. It is sent in the request body and must be protected as
                a secret.
            table_name: Target vector table or collection name.
            embedding_provider: Embedding provider identifier configured by
                the server.
            embedding_model: Embedding model identifier for vector creation.
            preset: Optional runtime preset; defaults to ``"balanced"``.
            **kwargs: Additional API request fields. These are merged after the
                named arguments, so matching keys override those values.

        Returns:
            Decoded JSON ingestion result from ``POST /ingest``.

        Raises:
            httpx.HTTPStatusError: If the server rejects the source or returns
                another non-success status.
            httpx.RequestError: If the request cannot be completed.
            ValueError: If the response body is not valid JSON.

        Side effects:
            Sends the full request, including the connection string, to the
            configured server. The server may read the source and write vectors
            to the selected collection.
        """
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
        """Run a retrieval-augmented generation query against an indexed store.

        Args:
            question: User query to retrieve context for and answer.
            connection_string: Database connection string used by retrieval;
                it is sent in the request body and must be protected as a
                secret.
            table_name: Vector table or collection to search.
            embedding_provider: Embedding provider identifier configured by
                the server.
            embedding_model: Embedding model identifier used for the query.
            llm_provider: Language-model provider identifier.
            llm_model: Language-model identifier for answer generation.
            system_prompt: Instructions supplied to the generation model.
            preset: Optional runtime preset; defaults to ``"balanced"``.
            **kwargs: Additional API request fields. These are merged after the
                named arguments, so matching keys override those values.

        Returns:
            Decoded JSON RAG result from ``POST /rag/query``.

        Raises:
            httpx.HTTPStatusError: If the server rejects the query or returns
                another non-success status.
            httpx.RequestError: If the request cannot be completed.
            ValueError: If the response body is not valid JSON.

        Side effects:
            Sends the question, prompt, model selections, and connection string
            to the configured server. The server may query the vector store and
            invoke the configured language model.
        """
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
