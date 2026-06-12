# docpipe — Future improvements plan

**Date:** 2026-06-12  
**Status:** In progress (v0.6.0 shipped; backlog execution ongoing)  
**Depends on:** Plugin expansion + profiles/presets (Phases A–D) — **complete**

---

## 1. Release & ops (P0)

- [x] Commit `feat/plugin-expansion`, tag `v0.6.0`, GitHub release
- [ ] Publish Docker tags: `slim`, `balanced`, `quality`, `agents` (CI matrix fixed; release workflow running)
- [ ] Update docpipe-site `lib/docs-content.ts` (profiles, presets, `/profiles`, `/plugins/resolve`) — repo not in monorepo
- [x] K8s manifest uses `ghcr.io/.../docpipe:balanced` + `DOCPIPE_PROFILE`
- [x] `CHANGELOG.md` `0.6.0` section

---

## 2. Plugin hardening (P1)

- [ ] **MinerU / PaddleOCR** — integration tests against real sample PDFs; fix API drift
- [ ] **pymupdf** — opt-in only; commercial license doc page
- [ ] **LightRAG** — wire ingest → LightRAG index sync or document two-phase setup
- [x] **LangGraph agent** — retrieval-only tool path (no duplicate full RAG query)
- [ ] **RAGAS** — pin ragas v0.4+ API; mock integration tests
- [ ] **deepeval** — CI evaluator extra (`profile-eval-ci`)

---

## 3. User experience (P1)

- [x] **CLI**: `docpipe plugins list`, `docpipe profiles list`, `docpipe resolve <file>`
- [x] **Homepage** (`GET /`) — install profile + runtime preset cards
- [x] **OpenAPI examples** for `preset` on ingest/RAG/parse
- [ ] **Delegate app** — assistant `docpipe_preset` field + create-flow selector (in progress)
- [ ] **Jingo/Andocs** — store `preset` per workspace; sync from `GET /profiles` on boot

---

## 4. Performance & scale (P2)

- [ ] Lazy-load heavy models (BGE, GLM-OCR) on first use
- [ ] Model cache dir env (`DOCPIPE_MODEL_CACHE`)
- [ ] GPU node pool + `profile-gpu` HPA in k8s
- [ ] Parser result cache (Redis) keyed by source hash
- [ ] Streaming ingest progress SSE

---

## 5. Security & multi-tenant (P2)

- [ ] Per-tenant allowlists via API key → plugin policy (not only global env)
- [ ] SSRF hardening audit for new parsers
- [ ] Rate limits per preset (quality tier lower QPS)
- [ ] Audit log for plugin resolution decisions

---

## 6. Observability (P2)

- [ ] Phoenix eval traces when `DOCPIPE_PHOENIX_ENABLED=true`
- [x] Prometheus metrics: `docpipe_preset_usage_total`, `docpipe_plugin_denied_total`
- [x] OTEL span attributes: `docpipe.preset`, `docpipe.profile` on ingest (parse/RAG via preset counter)

---

## 7. Architecture (P3)

- [ ] **MCP server** — real implementation replacing `agents/mcp_tools.py` stubs
- [ ] **Plugin marketplace** — third-party entry points with signature verification
- [ ] **Split GPU workers** — parse-heavy jobs on separate deployment from API
- [ ] **Microsoft Agent Framework** — migration path from AutoGen

---

## 8. Research backlog (P3)

- [ ] OmniDocBench-driven default tier per MIME type
- [ ] ColBERT / late interaction retrieval option
- [ ] Vision-RAG for image-heavy assistants
- [ ] Cost estimator API (preset + page count → $)

---

## Success metrics

| Metric | Target |
|--------|--------|
| Default image size (`balanced`) | < 2 GB |
| P95 `/parse` (10-page PDF, balanced) | < 15s |
| Plugin denied errors | < 1% of requests |
| RAGAS faithfulness (golden set) | > 0.85 on balanced preset |
