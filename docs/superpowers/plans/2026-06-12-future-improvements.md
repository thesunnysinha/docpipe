# docpipe — Future improvements plan

**Date:** 2026-06-12  
**Status:** Backlog (post v0.6 profiles/presets)  
**Depends on:** Plugin expansion + profiles/presets (Phases A–D)

---

## 1. Release & ops (P0)

- [ ] Commit `feat/plugin-expansion`, tag `v0.6.0`, GitHub release
- [ ] Publish Docker tags: `slim`, `balanced`, `quality`, `agents` (CI matrix in `.github/workflows/docker.yml`)
- [ ] Update docpipe-site `lib/docs-content.ts` (profiles, presets, `/profiles`, `/plugins/resolve`)
- [ ] Redeploy common-services with `ghcr.io/.../docpipe:balanced`
- [ ] Fill `CHANGELOG.md` `[Unreleased]` → `0.6.0`

---

## 2. Plugin hardening (P1)

- [ ] **MinerU / PaddleOCR** — integration tests against real sample PDFs; fix API drift
- [ ] **pymupdf** — opt-in only; commercial license doc page
- [ ] **LightRAG** — wire ingest → LightRAG index sync or document two-phase setup
- [ ] **LangGraph agent** — remove duplicate RAG query; add tests
- [ ] **RAGAS** — pin ragas v0.4+ API; mock integration tests
- [ ] **deepeval** — CI evaluator extra (`profile-eval-ci`)

---

## 3. User experience (P1)

- [ ] **CLI**: `docpipe plugins list`, `docpipe profiles`, `docpipe resolve <file>`
- [ ] **Homepage** (`GET /`) — show install profile + preset cards
- [ ] **OpenAPI examples** for `preset` on ingest/RAG
- [ ] **Delegate app** — assistant setting “Document processing: Fast / Balanced / Quality” calling `DocpipeClient`
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
- [ ] Prometheus metrics: `docpipe_preset_usage_total`, `docpipe_plugin_denied_total`
- [ ] OTEL span attributes: `docpipe.preset`, `docpipe.parser`, `docpipe.profile`

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
