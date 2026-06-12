# docpipe — Future improvements plan

**Date:** 2026-06-12  
**Status:** In progress (v0.6.0 shipped; backlog largely implemented on `feat/server-refactor`)  
**Depends on:** Plugin expansion + profiles/presets (Phases A–D) — **complete**

---

## 1. Release & ops (P0)

- [x] Commit `feat/plugin-expansion`, tag `v0.6.0`, GitHub release
- [x] Publish Docker tags: `slim`, `balanced`, `quality`, `agents` (CI matrix + per-profile release tags; `workflow_dispatch`)
- [x] Update docpipe-site `lib/docs-content.ts` (profiles, presets, `/profiles`, `/plugins/resolve`, ingest stream, MCP, cost, control DB, examples) — **docpipe-site repo**
- [x] K8s manifest uses `ghcr.io/.../docpipe:balanced` + `DOCPIPE_PROFILE`
- [x] `CHANGELOG.md` `0.6.0` section

---

## 2. Plugin hardening (P1)

- [x] **MinerU / PaddleOCR** — mocked contract tests (`test_mineru_parser.py`, `test_paddleocr_parser.py`)
- [x] **pymupdf** — opt-in only; commercial license page at `GET /licenses/pymupdf`
- [x] **LightRAG** — `graph_index` + `lightrag_working_dir` on ingest; `docs/LIGHTRAG.md`
- [x] **LangGraph agent** — retrieval-only tool path (no duplicate full RAG query)
- [x] **RAGAS** — pin `ragas>=0.4`; mock tests in `test_ragas_evaluator.py`
- [x] **deepeval** — `profile-eval-ci` extra + `tests/eval/` CI job

---

## 3. User experience (P1)

- [x] **CLI**: `docpipe plugins list`, `docpipe profiles list`, `docpipe resolve <file>`
- [x] **Homepage** (`GET /`) — Jinja templates (`base.html`, `homepage.html`)
- [x] **OpenAPI examples** for `preset` on ingest/RAG/parse
- [x] **Delegate app** — `docpipe_preset` on `feat/fastapi-backend` (delegate repo; merge pending)
- [ ] **Jingo/Andocs** — store `preset` per workspace; sync from `GET /profiles` on boot — **external**

---

## 4. Performance & scale (P2)

- [x] Lazy-load heavy models (BGE cross-encoder, GLM-OCR via `_get_ocr()`)
- [x] Model cache dir env (`DOCPIPE_MODEL_CACHE_DIR`)
- [x] GPU node pool + `profile-gpu` HPA in k8s (`deployment-gpu.yaml`, `hpa-gpu.yaml`)
- [x] Parser result cache (in-memory, `DOCPIPE_PARSER_CACHE_TTL_SECONDS`)
- [x] Streaming ingest progress SSE — `POST /ingest/stream`

---

## 5. Security & multi-tenant (P2)

- [x] Per-tenant allowlists via `X-Docpipe-Tenant-Id` + `DOCPIPE_TENANT_PLUGIN_POLICIES` JSON
- [x] SSRF hardening audit for new parsers (`url_safety.py`, `docs/SSRF_AUDIT.md`)
- [x] Rate limits per preset (`PresetRateLimitMiddleware`, `PRESET_RATE_LIMITS`)
- [x] Audit log for plugin resolution decisions (`profiles/audit.py`)

---

## 6. Observability (P2)

- [x] Phoenix eval traces when `DOCPIPE_PHOENIX_ENABLED=true` (`observability/phoenix.py`)
- [x] Prometheus metrics: `docpipe_preset_usage_total`, `docpipe_plugin_denied_total`
- [x] OTEL span attributes: `docpipe.preset`, `docpipe.profile` on ingest/parse/RAG

---

## 7. Architecture (P3)

- [x] **MCP server** — `GET /mcp/tools`, `POST /mcp/call` (replaces stubs)
- [ ] **Plugin marketplace** — third-party entry points with signature verification
- [ ] **Split GPU workers** — parse-heavy jobs on separate deployment from API
- [ ] **Microsoft Agent Framework** — migration path from AutoGen

---

## 8. Research backlog (P3)

- [ ] OmniDocBench-driven default tier per MIME type
- [ ] ColBERT / late interaction retrieval option
- [ ] Vision-RAG for image-heavy assistants
- [x] Cost estimator API — `POST /cost/estimate` (preset + page count → $)

---

## Success metrics

| Metric | Target |
|--------|--------|
| Default image size (`balanced`) | < 2 GB |
| P95 `/parse` (10-page PDF, balanced) | < 15s |
| Plugin denied errors | < 1% of requests |
| RAGAS faithfulness (golden set) | > 0.85 on balanced preset |
