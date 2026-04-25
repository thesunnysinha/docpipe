# docpipe API Completeness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the four most-requested production gaps to docpipe's API: document deletion, conversation history, streaming responses, and metadata filtering.

**Architecture:** Each improvement is a vertical slice — types → pipeline (where needed) → HTTP endpoint → test. All changes land in `src/docpipe/server/app.py`, `src/docpipe/core/types.py`, and optionally `src/docpipe/rag/pipeline.py`. No new infrastructure required.

**Tech Stack:** FastAPI, Pydantic v2, LangChain PGVector, psycopg2, pytest, httpx (for `TestClient`)

---

## File Structure

| File | Change |
|------|--------|
| `src/docpipe/server/app.py` | Add `DELETE /ingest`, `POST /rag/stream`; extend `RAGQueryRequest` with `history` + `filters` |
| `src/docpipe/core/types.py` | Add `history` + `filters` to `RAGConfig`; add `DeleteRequest` / `DeleteResponse` |
| `src/docpipe/rag/pipeline.py` | Thread `history` through `_generate()` and `_generate_stream()`; thread `filters` through all `_retrieve_*` methods |
| `tests/unit/test_api.py` | New — HTTP-level tests for DELETE + streaming + history + filter via FastAPI `TestClient` |
| `tests/unit/test_rag.py` | Extend — unit tests for history and filter plumbing inside `RAGPipeline` |

---

## Task 1: DELETE endpoint — remove ingested chunks by source

**Why:** Every production app needs document deletion. Without it, re-ingesting updated files accumulates stale chunks. Integrators are forced to use raw SQL (as Jingo does today).

**Files:**
- Modify: `src/docpipe/core/types.py`
- Modify: `src/docpipe/server/app.py`
- Create: `tests/unit/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_api.py
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from docpipe.server.app import create_app


@pytest.fixture()
def client():
    return TestClient(create_app())


@patch("docpipe.server.app.psycopg2")
def test_delete_by_source_removes_chunks(mock_psycopg2, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 3
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_psycopg2.connect.return_value.__enter__ = lambda s: mock_conn
    mock_psycopg2.connect.return_value.__exit__ = MagicMock(return_value=False)

    resp = client.request(
        "DELETE",
        "/ingest",
        json={
            "connection_string": "postgresql://test/db",
            "table_name": "docs",
            "source": "reports/q1.pdf",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["chunks_deleted"] == 3
    mock_cursor.execute.assert_called_once()
    call_args = mock_cursor.execute.call_args[0]
    assert "DELETE FROM" in call_args[0]
    assert "docs" in call_args[0]


@patch("docpipe.server.app.psycopg2")
def test_delete_table_not_found_returns_404(mock_psycopg2, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # Simulate table does not exist
    mock_cursor.execute.side_effect = Exception('relation "nonexistent" does not exist')
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_psycopg2.connect.return_value.__enter__ = lambda s: mock_conn
    mock_psycopg2.connect.return_value.__exit__ = MagicMock(return_value=False)

    resp = client.request(
        "DELETE",
        "/ingest",
        json={
            "connection_string": "postgresql://test/db",
            "table_name": "nonexistent",
            "source": "doc.pdf",
        },
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/sunny/Desktop/Projects/docpipe
.venv/bin/pytest tests/unit/test_api.py::test_delete_by_source_removes_chunks -v
```
Expected: FAIL with `ImportError` or `404 != 200`

- [ ] **Step 3: Add `DeleteRequest` and `DeleteResponse` to types**

In `src/docpipe/core/types.py`, add after `IngestionResult`:

```python
class DeleteRequest(BaseModel):
    """Request to delete chunks by source from a pgvector table."""

    connection_string: str
    table_name: str
    source: str


class DeleteResponse(BaseModel):
    """Result of a delete operation."""

    table_name: str
    source: str
    chunks_deleted: int
```

- [ ] **Step 4: Add DELETE /ingest endpoint to app.py**

In `src/docpipe/server/app.py`, add `import psycopg2` at the top of `create_app()` (inside the function to keep it optional), and add after the `/ingest` endpoint:

```python
    @app.delete("/ingest", response_model=DeleteResponse)
    async def delete_document(req: DeleteRequest) -> DeleteResponse:
        import psycopg2

        try:
            with psycopg2.connect(req.connection_string) as conn:
                with conn.cursor() as cur:
                    sql = (
                        f"DELETE FROM {req.table_name} "  # noqa: S608
                        "WHERE cmetadata->>'source' = %s"
                    )
                    cur.execute(sql, [req.source])
                    deleted = cur.rowcount
            return DeleteResponse(
                table_name=req.table_name,
                source=req.source,
                chunks_deleted=deleted,
            )
        except Exception as exc:
            if "does not exist" in str(exc):
                raise HTTPException(status_code=404, detail=f"Table '{req.table_name}' not found") from exc
            raise HTTPException(status_code=500, detail=str(exc)) from exc
```

Also add to the imports at the top of the file:
```python
from docpipe.core.types import DeleteRequest, DeleteResponse
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/unit/test_api.py -v
```
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add src/docpipe/core/types.py src/docpipe/server/app.py tests/unit/test_api.py
git commit -m "feat: add DELETE /ingest endpoint for chunk removal by source"
```

---

## Task 2: Conversation history in RAG

**Why:** Real chat applications need to reference prior turns ("what did I ask before?"). Currently each query is stateless. History is passed as LangChain `AIMessage`/`HumanMessage` pairs prepended to the prompt.

**Files:**
- Modify: `src/docpipe/core/types.py`
- Modify: `src/docpipe/rag/pipeline.py`
- Modify: `src/docpipe/server/app.py`
- Modify: `tests/unit/test_rag.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_rag.py`:

```python
@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_query_passes_history_to_llm(mock_llm_factory, mock_emb_factory):
    from langchain_core.messages import AIMessage, HumanMessage

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="answer")
    mock_llm_factory.return_value = mock_llm
    mock_emb_factory.return_value = MagicMock()

    config = _make_config(
        history=[
            {"role": "user", "content": "What is RAG?"},
            {"role": "assistant", "content": "RAG stands for retrieval-augmented generation."},
        ]
    )
    pipeline = RAGPipeline(config)

    with patch.object(pipeline, "_naive_query") as mock_naive:
        mock_naive.return_value = RAGResult(
            query="follow-up",
            answer="",
            strategy="naive",
            chunks=[],
            sources=[],
            timing_seconds=0.0,
        )
        # Trigger generate via query — mock dispatch
        with patch.object(pipeline, "_retrieve_naive", return_value=[]):
            with patch.object(pipeline, "_generate", wraps=pipeline._generate) as mock_gen:
                pipeline.query("follow-up")

    # _generate should have been called; llm.invoke should include history messages
    call_messages = mock_llm.invoke.call_args[0][0]
    contents = [m.content for m in call_messages]
    assert any("What is RAG?" in c for c in contents)
    assert any("RAG stands for" in c for c in contents)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/unit/test_rag.py::test_query_passes_history_to_llm -v
```
Expected: FAIL (history field does not exist in RAGConfig)

- [ ] **Step 3: Add `history` field to `RAGConfig` in types.py**

In `src/docpipe/core/types.py`, add to `RAGConfig`:

```python
    # Conversation history: list of {"role": "user"|"assistant", "content": str}
    history: list[dict[str, str]] = Field(default_factory=list)
```

Place it after `system_prompt: str | None = None`.

- [ ] **Step 4: Thread history through `_generate()` and `_generate_stream()` in pipeline.py**

Replace `_generate` in `src/docpipe/rag/pipeline.py`:

```python
    def _generate(self, question: str, context: str) -> tuple[str, Any]:
        """Generate an answer. Returns (text, structured_or_None)."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        system_text = (self._config.system_prompt or DEFAULT_SYSTEM_PROMPT).format(
            context=context, question=question
        )

        messages: list[Any] = [SystemMessage(content=system_text)]
        for turn in self._config.history:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                messages.append(AIMessage(content=turn["content"]))
        messages.append(HumanMessage(content=question))

        if self._config.output_model is not None:
            structured_llm = self._llm.with_structured_output(self._config.output_model)
            result = structured_llm.invoke(messages)
            return result.model_dump_json(), result

        response = self._llm.invoke(messages)
        return response.content, None
```

Replace `_generate_stream` in `src/docpipe/rag/pipeline.py`:

```python
    def _generate_stream(self, question: str, context: str) -> Iterator[str]:
        """Stream answer tokens from the LLM."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        system_text = (self._config.system_prompt or DEFAULT_SYSTEM_PROMPT).format(
            context=context, question=question
        )
        messages: list[Any] = [SystemMessage(content=system_text)]
        for turn in self._config.history:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                messages.append(AIMessage(content=turn["content"]))
        messages.append(HumanMessage(content=question))

        for chunk in self._llm.stream(messages):
            yield chunk.content
```

- [ ] **Step 5: Add `history` to `RAGQueryRequest` in app.py and wire to `RAGConfig`**

In `src/docpipe/server/app.py`, add to `RAGQueryRequest`:
```python
    history: list[dict[str, str]] = Field(default_factory=list)
```

In the `rag_query` handler inside `create_app()`, add `history=req.history` to the `RAGConfig(...)` constructor call.

- [ ] **Step 6: Run tests**

```bash
.venv/bin/pytest tests/unit/test_rag.py -v
```
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/docpipe/core/types.py src/docpipe/rag/pipeline.py src/docpipe/server/app.py tests/unit/test_rag.py
git commit -m "feat: add conversation history support to RAG query"
```

---

## Task 3: Streaming HTTP endpoint (POST /rag/stream)

**Why:** `RAGPipeline.stream_query()` already yields tokens but no HTTP endpoint exposes it. Clients need Server-Sent Events (SSE) to stream answers without waiting for full generation.

**Files:**
- Modify: `src/docpipe/server/app.py`
- Modify: `tests/unit/test_api.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_api.py`:

```python
@patch("docpipe.server.app.RAGConfig")
@patch("docpipe.server.app.RAGPipeline")
def test_rag_stream_returns_event_stream(MockPipeline, MockConfig, client):
    mock_pipeline = MagicMock()
    mock_pipeline.stream_query.return_value = iter(["Hello", " world", "!"])
    MockPipeline.return_value = mock_pipeline

    resp = client.post(
        "/rag/stream",
        json={
            "question": "What is docpipe?",
            "connection_string": "postgresql://test/db",
            "table_name": "docs",
            "embedding_provider": "openai",
            "embedding_model": "text-embedding-3-small",
            "llm_provider": "openai",
            "llm_model": "gpt-4o",
        },
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "data: Hello" in body
    assert "data:  world" in body
    assert "data: !" in body
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/unit/test_api.py::test_rag_stream_returns_event_stream -v
```
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Add `POST /rag/stream` endpoint to app.py**

Add to `create_app()` in `src/docpipe/server/app.py`, after the `/rag/query` handler:

```python
    @app.post("/rag/stream")
    async def rag_stream(req: RAGQueryRequest) -> StreamingResponse:
        from fastapi.responses import StreamingResponse as _SR

        from docpipe.core.types import RAGConfig
        from docpipe.rag.pipeline import RAGPipeline

        config = RAGConfig(
            connection_string=req.connection_string,
            table_name=req.table_name,
            embedding_provider=req.embedding_provider,
            embedding_model=req.embedding_model,
            llm_provider=req.llm_provider,
            llm_model=req.llm_model,
            strategy=req.strategy,
            top_k=req.top_k,
            system_prompt=req.system_prompt,
            hyde_prompt=req.hyde_prompt,
            multi_query_count=req.multi_query_count,
            parent_window_size=req.parent_window_size,
            hybrid_bm25_weight=req.hybrid_bm25_weight,
            reranker=req.reranker,
            reranker_model=req.reranker_model,
            rerank_top_n=req.rerank_top_n,
            history=req.history,
            stream=True,
        )
        pipeline = RAGPipeline(config)

        async def event_generator():
            for token in pipeline.stream_query(req.question):
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"

        return _SR(event_generator(), media_type="text/event-stream")
```

Also add `from fastapi.responses import StreamingResponse` to the top of `src/docpipe/server/app.py`.

- [ ] **Step 4: Run tests**

```bash
.venv/bin/pytest tests/unit/test_api.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/docpipe/server/app.py tests/unit/test_api.py
git commit -m "feat: add POST /rag/stream endpoint for Server-Sent Events streaming"
```

---

## Task 4: Metadata filtering in search and RAG

**Why:** Multi-tenant apps and scoped searches need to filter by metadata (e.g. `{"user_id": "u123"}` or `{"source": "policy.pdf"}`). LangChain PGVector accepts a `filter` kwarg in `similarity_search_with_score()`.

**Files:**
- Modify: `src/docpipe/core/types.py`
- Modify: `src/docpipe/rag/pipeline.py`
- Modify: `src/docpipe/server/app.py`
- Modify: `tests/unit/test_rag.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_rag.py`:

```python
@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
@patch.object(RAGPipeline, "_get_vectorstore")
def test_naive_query_passes_filters_to_vectorstore(mock_vs_factory, mock_llm_factory, mock_emb_factory):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="answer")
    mock_llm_factory.return_value = mock_llm
    mock_emb_factory.return_value = MagicMock()

    mock_vs = MagicMock()
    mock_vs.similarity_search_with_score.return_value = []
    mock_vs_factory.return_value = mock_vs

    config = _make_config(filters={"user_id": "u123", "category": "finance"})
    pipeline = RAGPipeline(config)
    pipeline.query("test question")

    call_kwargs = mock_vs.similarity_search_with_score.call_args[1]
    assert call_kwargs.get("filter") == {"user_id": "u123", "category": "finance"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/unit/test_rag.py::test_naive_query_passes_filters_to_vectorstore -v
```
Expected: FAIL (`filters` field not in `RAGConfig`)

- [ ] **Step 3: Add `filters` to `RAGConfig` in types.py**

In `src/docpipe/core/types.py`, add to `RAGConfig`:

```python
    # Metadata filters passed to pgvector similarity search
    filters: dict[str, Any] = Field(default_factory=dict)
```

Place after `history: list[dict[str, str]]`.

- [ ] **Step 4: Thread filters through all `_retrieve_*` methods in pipeline.py**

In `src/docpipe/rag/pipeline.py`, add a helper property:

```python
    @property
    def _filters(self) -> dict | None:
        return self._config.filters or None
```

Then in every `_retrieve_*` method, wherever `similarity_search_with_score` is called, add `filter=self._filters`. For example, `_retrieve_naive`:

```python
    def _retrieve_naive(self, question: str) -> list[RAGChunk]:
        vs = self._get_vectorstore()
        docs = vs.similarity_search_with_score(
            question, k=self._config.top_k, filter=self._filters
        )
        return self._docs_to_chunks(docs)
```

Apply the same change to `_retrieve_hyde`, `_retrieve_multi_query`, `_retrieve_parent_document`, and `_retrieve_hybrid`. Each of those methods calls `similarity_search_with_score` — add `filter=self._filters` to each call.

- [ ] **Step 5: Add `filters` to `RAGQueryRequest` and `SearchRequest` in app.py**

In `src/docpipe/server/app.py`, add to `RAGQueryRequest`:
```python
    filters: dict[str, Any] = Field(default_factory=dict)
```

Add to `SearchRequest`:
```python
    filters: dict[str, Any] = Field(default_factory=dict)
```

In the `rag_query` handler, add `filters=req.filters` to the `RAGConfig(...)` call.

In the `search_documents` handler, update the `ingestion.search()` call to pass filters:
```python
    results = ingestion.search(req.query, top_k=req.top_k, filters=req.filters)
```

Also update `IngestionPipeline.search()` signature in `src/docpipe/ingestion/pipeline.py` to accept and pass through `filters`:
```python
    def search(self, query: str, top_k: int = 10, filters: dict | None = None) -> list[dict]:
        vs = self._get_vectorstore()
        docs = vs.similarity_search_with_score(query, k=top_k, filter=filters)
        return [
            {
                "content": doc.page_content,
                "score": float(score),
                "metadata": doc.metadata,
            }
            for doc, score in docs
        ]
```

- [ ] **Step 6: Run all tests**

```bash
.venv/bin/pytest tests/unit/ -v
```
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/docpipe/core/types.py src/docpipe/rag/pipeline.py src/docpipe/ingestion/pipeline.py src/docpipe/server/app.py tests/unit/test_rag.py
git commit -m "feat: add metadata filtering to search and RAG endpoints"
```

---

## Self-Review

**Spec coverage:**
- ✅ DELETE endpoint — Task 1
- ✅ Conversation history — Task 2
- ✅ Streaming HTTP endpoint — Task 3
- ✅ Metadata filtering in search + RAG — Task 4

**Placeholder scan:** None found. All tasks include actual code, commands, and expected output.

**Type consistency:**
- `DeleteRequest` / `DeleteResponse` defined in Task 1 Step 3, used in Task 1 Step 4 — ✅
- `history: list[dict[str, str]]` defined in Task 2 Step 3, wired in Steps 4 and 5 — ✅
- `filters: dict[str, Any]` defined in Task 4 Step 3, wired in Steps 4 and 5 — ✅
- `self._filters` property in Task 4 Step 4, used in all `_retrieve_*` methods — ✅
- `RAGQueryRequest.history` added in Task 2 Step 5 before Task 3 uses it in `/rag/stream` handler — ✅

**Not in this plan (separate plans needed):**
- Async ingestion with job tracking — requires background task infrastructure
- API key authentication middleware — cross-cutting security concern
