# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Optional control-plane DB (SQLite in Docker) with Alembic migrations, seeded admin user, `/admin` panel
- Env-gated persistence: `DOCPIPE_PERSIST_AUDIT_EVENTS`, `DOCPIPE_PERSIST_INGEST_JOBS`, `DOCPIPE_PERSIST_PLUGIN_RESOLUTIONS`
- `POST /ingest/stream` SSE progress events for long ingest jobs
- `POST /cost/estimate` heuristic parse time and embedding cost by preset
- `GET /mcp/tools` and `POST /mcp/call` for agent tool discovery and invocation
- Jinja2 homepage templates (`server/templates/`), PyMuPDF license page (`GET /licenses/pymupdf`)
- LightRAG ingest sync (`graph_index`, `lightrag_working_dir`); `docs/LIGHTRAG.md`
- Preset rate limiting, tenant plugin policies (`X-Docpipe-Tenant-Id`), plugin resolve audit log
- Phoenix optional tracing (`DOCPIPE_PHOENIX_ENABLED`), model cache dir, in-memory parser cache
- GPU K8s manifests (`deployment-gpu.yaml`, `hpa-gpu.yaml`); Docker release tags per profile
- SSRF guards for quality parsers; `docs/SSRF_AUDIT.md`
- Tests: MinerU, PaddleOCR, RAGAS evaluator, DeepEval smoke (`tests/eval/`)

### Changed

- FastAPI server layered into `routers/` + `services/`; strict `ApiRequest`/`ApiResponse` schemas
- RAGAS pin `>=0.4`; GLM-OCR lazy model init; OTEL preset/profile on parse and RAG routes

## [0.6.0] - 2026-06-12

### Added

- Plugin registry groups: chunkers, rerankers, evaluators; enriched `GET /plugins`
- Install profiles (`profile-slim` … `profile-gpu`) and Docker `DOPIPE_PROFILE` build arg
- Runtime presets (`fast`, `balanced`, `quality`, `agents`) via `preset` on ingest/RAG APIs
- `GET /profiles`, `POST /plugins/resolve`, plugin allowlists (`DOCPIPE_ENABLED_*`, `DOCPIPE_DISABLED_PLUGINS`)
- Parsers: pymupdf, mineru, paddleocr, unstructured; `parser=auto` router
- Chunkers: semchunk, chonkie; rerankers: BGE, mxbai; evaluators: builtin, RAGAS
- `POST /agents/query` (AutoGen / LangGraph); LightRAG strategy; LangChain strict extract
- `DocpipeClient` integration helper; `docs/INTEGRATION.md`, `docs/PLUGIN_LICENSES.md`

### Changed

- Default parser server setting: `auto` (tier `balanced`)
- Docker: profile-specific tags (`:slim`, `:balanced`, `:quality`, `:agents`); `[all]` dev-only
- Eval pipeline delegates to evaluator plugins

### Fixed

- RAG reranking uses plugin registry instead of inline flashrank/cohere only


## [0.5.2] - 2026-05-19

### Changed

- README and CONTRIBUTING: documentation links use [docpipe.sunnysinha.online](https://docpipe.sunnysinha.online/docs); remove product-specific integration links from README
- CONTRIBUTING: reference in-repo files (README, `.env.example`, CHANGELOG) and current release workflow

## [0.5.1] - 2026-05-19

### Changed

- README streamlined (~102 lines); full documentation on [docpipe docs](https://docpipe.sunnysinha.online/docs) (install, API, env vars)
- README: drop redundant git install URLs now that `docpipe-sdk` is on PyPI

## [0.5.0] - 2026-05-19

### Added

- Optional **turbovec** vector backend (`DOCPIPE_VECTOR_BACKEND`, `[turbovec]` extra, per-request `vector_backend`)
- OpenTelemetry tracing (`[observability]`), Prometheus `/metrics`, token `usage` on RAG responses
- `POST /generate` plain LLM completion; `docpipe.http.DocpipeClient` (`[http]` extra)
- Richer `/health` with optional DB and embedding probes
- HTTP Basic Auth (`DOCPIPE_AUTH_ENABLED`, `DOCPIPE_USERNAME`, `DOCPIPE_PASSWORD`)
- `DOCPIPE_ALLOW_PRIVATE_URLS` for Docker/MinIO presigned ingest sources

### Changed

- **Breaking:** top-level `docpipe.rag()` renamed to `docpipe.query()` (avoid shadowing `docpipe.rag` package)
- README, `.env.example`: document all `DOCPIPE_*` settings; fix compose env var names

### Fixed

- Docling parser: `doc.pages` dict iteration (`pages.items()`)
- Upstream embedding failures return HTTP 502 with structured `detail`


## [0.4.5] - 2026-04-26

PyPI release (predates items in Unreleased above; install from `main` for latest).

## [0.4.2] - 2026-04-12

### Changed

- README: add Docker / Docker Compose quickstart, GHCR image reference and tags table
- README: add `anthropic` to install options, update RAG strategies table with `auto` (6 total)
- Add `docker-compose.yml` (server + pgvector), `docker-compose.full.yml` (+ Adminer), `.env.example`

## [0.4.1] - 2026-04-11

### Fixed

- `LangExtractExtractor`: changed `lx.extract(text=text, ...)` to positional arg `lx.extract(text, ...)` to match updated API
- `LangExtractExtractor`: fixed `e.char_interval[0]`/`[1]` → `e.char_interval.start`/`.end` for `CharInterval` named attributes
- `LangExtractExtractor`: fixed import paths — `ExampleData` and `Extraction` now imported from `langextract.data`
- `LangExtractExtractor`: provide a minimal placeholder example when `schema.examples` is empty (LangExtract requires at least one)
- `RAGPipeline` hybrid strategy: changed `from langchain.retrievers` → `from langchain_classic.retrievers` for `EnsembleRetriever`
- Added missing optional deps: `psycopg2-binary` to `[pgvector]`, `rank-bm25` and `langchain-classic` to `[rag]`, new `[anthropic]` extra for `langchain-anthropic`

## [0.4.0] - 2026-04-05

### Added

- GLM-OCR as optional parser backend — state-of-the-art multimodal OCR (0.9B params, #1 on OmniDocBench V1.5)
  - Install: `pip install "docpipe-sdk[glm-ocr]"`
  - Usage: `docpipe.parse("doc.pdf", parser="glm-ocr")`
  - Supports Cloud API (MaaS) and self-hosted (vLLM/SGLang) modes
  - Best for scanned documents, complex tables, formulas, code-heavy layouts

## [0.3.0] - 2026-04-04

### Added

- Contextual Chunk Injection — LLM prepends situational context to each chunk before embedding (`IngestionConfig(contextual_injection=True)`)
- Semantic Query Cache — cosine-similarity cache avoids redundant LLM calls for near-duplicate queries (`RAGConfig(cache_enabled=True, cache_similarity_threshold=0.95)`)
- Domain-specific chunk methods — 7 document-type-aware chunking strategies: `paper`, `laws`, `book`, `qa`, `manual`, `table`, `presentation` (`IngestionConfig(chunk_method="paper")`)
- Streaming RAG — `RAGPipeline.stream_query()` and `docpipe.stream_query()` return `Iterator[str]` of answer tokens (`RAGConfig(stream=True)`)
- Agentic RAG — `strategy="auto"` lets the LLM classify the question and dispatch to the optimal strategy; result includes `metadata["auto_selected_strategy"]`

## [0.2.1] - 2026-04-04

### Fixed

- Updated PyPI package description to include RAG pipeline (was missing from the one-liner)
- Added `pgvector`, `embeddings`, `retrieval` to package keywords for better discoverability
- Interactive Code Playground added to landing page — configure any pipeline and get copy-ready Python code

## [0.2.0] - 2026-04-04

### Added

- `RAGPipeline` with 5 retrieval strategies: naive, HyDE, multi-query, parent-document, hybrid
- HyDE (Hypothetical Document Embeddings) — LLM generates hypothetical answer, embeds it for retrieval
- Multi-query expansion — expands query into N variants, unions and deduplicates results
- Parent-document window expansion — expands context around seed chunks via source metadata filter
- Hybrid search — combines dense vector search with BM25 keyword retrieval (EnsembleRetriever)
- Optional cross-encoder reranking via FlashRank (local) or Cohere (cloud API)
- Structured RAG output — `RAGConfig(output_model=MyModel)` returns typed Pydantic object via `result.structured`
- `EvalPipeline` for measuring RAG quality: hit rate, MRR, faithfulness, answer similarity (LLM-as-judge)
- Incremental ingestion — `IngestionConfig(incremental=True)` skips unchanged files via SHA-256 hash
- `docpipe rag query` CLI command with all strategy and reranker flags
- `docpipe evaluate run` CLI command for running Q&A evaluation files
- `POST /rag/query` and `POST /evaluate/run` FastAPI endpoints
- `rag()` and new type exports (`RAGConfig`, `RAGChunk`, `RAGResult`, `EvalPipeline`, etc.) in public API
- New optional extras: `[rag]` (langchain-community for BM25), `[rerank]` (flashrank)
- `CONTRIBUTING.md` with plugin development walkthrough
- Updated landing page with RAG section, 5 strategy cards, stats bar, and structured output examples
- 19 new unit tests for RAGPipeline and EvalPipeline (53 total, all passing)

## [0.1.0] - 2026-04-04

### Added

- Core pipeline architecture with Protocol-based parser and extractor interfaces
- Docling parser adapter for document parsing (PDF, DOCX, images, audio, video)
- LangExtract extractor adapter for LLM-based structured extraction
- LangChain extractor adapter using `with_structured_output()`
- Ingestion pipeline with LangChain text splitters, embeddings, and PGVector
- Plugin registry with `importlib.metadata` entry-point auto-discovery
- Configuration via Pydantic Settings (env vars + YAML files)
- CLI commands: `parse`, `extract`, `run`, `ingest`, `search`, `serve`, `plugins`, `config`
- FastAPI server with REST endpoints for all pipeline operations
- Dockerfile for containerized deployment
- 34 unit tests with mock parser/extractor

[Unreleased]: https://github.com/thesunnysinha/docpipe/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/thesunnysinha/docpipe/compare/v0.4.5...v0.5.0
[0.3.0]: https://github.com/thesunnysinha/docpipe/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/thesunnysinha/docpipe/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/thesunnysinha/docpipe/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/thesunnysinha/docpipe/releases/tag/v0.1.0
[0.1.0]: https://github.com/thesunnysinha/docpipe/releases/tag/v0.1.0
