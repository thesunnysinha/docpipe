# Graph Report - /Users/sunny/Desktop/Projects/docpipe  (2026-04-27)

## Corpus Check
- Corpus is ~21,707 words - fits in a single context window. You may not need a graph.

## Summary
- 733 nodes · 2340 edges · 40 communities detected
- Extraction: 39% EXTRACTED · 61% INFERRED · 0% AMBIGUOUS · INFERRED: 1433 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `PluginRegistry` - 96 edges
2. `RAGPipeline` - 93 edges
3. `ParsedDocument` - 85 edges
4. `ExtractionSchema` - 84 edges
5. `IngestionConfig` - 80 edges
6. `IngestionPipeline` - 77 edges
7. `RAGConfig` - 75 edges
8. `ConfigurationError` - 69 edges
9. `Pipeline` - 64 edges
10. `ExtractionResult` - 60 edges
11. `EvalPipeline` - 60 edges
12. `DocumentFormat` - 58 edges
13. `EvalQuestion` - 51 edges
14. `EvalConfig` - 51 edges
15. `DocpipeError` - 42 edges

## Surprising Connections (you probably didn't know these)
- `CHANGELOG v0.1.0 - Core Architecture` --rationale_for--> `PluginRegistry`  [INFERRED]
  CHANGELOG.md → /Users/sunny/Desktop/Projects/docpipe/src/docpipe/registry/registry.py
- `CHANGELOG v0.2.0 - RAG Pipeline + Eval` --rationale_for--> `RAGPipeline._rerank (FlashRank/Cohere)`  [INFERRED]
  CHANGELOG.md → src/docpipe/rag/pipeline.py
- `README: Plugin System (Entry Points)` --references--> `PluginRegistry`  [EXTRACTED]
  README.md → /Users/sunny/Desktop/Projects/docpipe/src/docpipe/registry/registry.py
- `CONTRIBUTING: Plugin Development Guide` --references--> `PluginRegistry`  [EXTRACTED]
  CONTRIBUTING.md → /Users/sunny/Desktop/Projects/docpipe/src/docpipe/registry/registry.py
- `Plan Task 2: Conversation History in RAG` --rationale_for--> `RAGQueryRequest Model`  [INFERRED]
  docs/superpowers/plans/2026-04-26-api-completeness.md → src/docpipe/server/app.py
- `README: API Endpoints Reference Table` --references--> `DELETE /ingest Endpoint`  [EXTRACTED]
  README.md → src/docpipe/server/app.py
- `Plan Task 1: DELETE /ingest Endpoint` --rationale_for--> `DELETE /ingest Endpoint`  [EXTRACTED]
  docs/superpowers/plans/2026-04-26-api-completeness.md → src/docpipe/server/app.py
- `Plan Task 4: Metadata Filtering in Search + RAG` --rationale_for--> `POST /search Endpoint`  [INFERRED]
  docs/superpowers/plans/2026-04-26-api-completeness.md → src/docpipe/server/app.py

## Hyperedges (group relationships)
- **Server App Integration Test Suite** — test_metadata_filtering, test_rag_stream, test_api [INFERRED 0.90]
- **RAG Pipeline Test Coverage** — test_rag, test_improvements, test_eval, test_rag_stream [INFERRED 0.88]
- **Tests Using conftest Mock Fixtures** — test_pipeline, test_registry, conftest_MockParser, conftest_MockExtractor [EXTRACTED 1.00]
- **run.py CLI Commands** — run_cmd_test, run_cmd_lint, run_cmd_build, run_cmd_serve, run_cmd_release [EXTRACTED 1.00]
- **Modules Consuming Core Types** — test_types, test_rag, test_eval, test_ingestion, test_improvements, conftest_MockParser, conftest_MockExtractor [INFERRED 0.85]
- **BaseParser Protocol Implementors** — core_parser_BaseParser, docling_parser_DoclingParser, glm_ocr_parser_GLMOCRParser [INFERRED 0.90]
- **Pipeline Core Type Contract** — core_types_ParsedDocument, core_types_ExtractionResult, core_types_PipelineResult, core_types_IngestionConfig, core_types_IngestionResult [INFERRED 0.85]
- **RAG Pipeline Type Contract** — core_types_RAGConfig, core_types_RAGChunk, core_types_RAGResult [EXTRACTED 1.00]
- **Evaluation Pipeline Type Contract** — core_types_EvalConfig, core_types_EvalQuestion, core_types_EvalMetrics, core_types_EvalResult [EXTRACTED 1.00]
- **DocpipeError Exception Hierarchy** — core_errors_DocpipeError, core_errors_ParseError, core_errors_ExtractionError, core_errors_IngestionError, core_errors_ConfigurationError, core_errors_ParserNotFoundError, core_errors_ExtractorNotFoundError, core_errors_ParserNotInstalledError, core_errors_ExtractorNotInstalledError, core_errors_UnsupportedFormatError, core_errors_RAGError, core_errors_EvalError [EXTRACTED 1.00]
- **Private URL SSRF Bypass Design** — config_settings_allow_private_urls, docling_parser_resolve_source, docling_parser_is_private_url, rationale_allow_private_urls_ssrf, rationale_resolve_source_pre_fetch [EXTRACTED 1.00]
- **Optional Plugin Registration Pattern** — init_register_builtins, docling_parser_DoclingParser, glm_ocr_parser_GLMOCRParser, rationale_optional_deps_try_import [EXTRACTED 1.00]
- **require_auth Dependency Injected Into All Protected Endpoints** — server_auth_require_auth, server_app_endpoint_parse, server_app_endpoint_extract, server_app_endpoint_run, server_app_endpoint_ingest, server_app_endpoint_delete_ingest, server_app_endpoint_search, server_app_endpoint_plugins, server_app_endpoint_rag_query, server_app_endpoint_rag_stream, server_app_endpoint_evaluate, server_app_endpoint_generate [EXTRACTED 1.00]
- **RAGPipeline Six Retrieval Strategies** — rag_pipeline_ragpipeline, rag_pipeline_strategy_naive, rag_pipeline_strategy_hyde, rag_pipeline_strategy_multi_query, rag_pipeline_strategy_parent_document, rag_pipeline_strategy_hybrid, rag_pipeline_strategy_auto [EXTRACTED 1.00]
- **EvalPipeline Four RAG Quality Metrics** — eval_pipeline_evalpipeline, eval_pipeline_metric_hit_rate, eval_pipeline_metric_mrr, eval_pipeline_metric_faithfulness, eval_pipeline_metric_answer_similarity [EXTRACTED 1.00]
- **PluginRegistry Decouples LangExtract and LangChain Extractors from Server** — registry_pluginregistry, extractors_langextract_extractor, extractors_langchain_extractor, server_app_endpoint_extract [INFERRED 0.90]
- **API Completeness Plan: 4 Production Feature Tasks** — plan_api_completeness, plan_task1_delete_endpoint, plan_task2_history, plan_task3_streaming, plan_task4_filters [EXTRACTED 1.00]
- **CLI Commands Mirror HTTP Endpoints (parse/extract/run/ingest/search/rag/evaluate)** — cli_main_cmd_parse, cli_main_cmd_extract, cli_main_cmd_run, cli_main_cmd_ingest, cli_main_cmd_search, cli_main_cmd_rag_query, cli_main_cmd_evaluate_run, server_app_endpoint_parse, server_app_endpoint_extract, server_app_endpoint_run, server_app_endpoint_ingest, server_app_endpoint_search, server_app_endpoint_rag_query, server_app_endpoint_evaluate [INFERRED 0.85]

## Communities

### Community 0 - "Pipeline Ragpipeline"
Cohesion: 0.1
Nodes (97): create_app(), EvaluateRequest, EvaluateResponse, ExtractRequest, ExtractResponse, GenerateRequest, GenerateResponse, HealthResponse (+89 more)

### Community 1 - "Registry Pluginregistry"
Cohesion: 0.05
Nodes (85): CLI extract Command, CLI ingest Command, CLI parse Command, CLI plugins list Command, CONTRIBUTING: Plugin Development Guide, DocpipeError, EvalError, ExtractionError (+77 more)

### Community 2 - "Types Documentformat"
Cohesion: 0.07
Nodes (41): _detect_format(), DoclingParser, is_available(), _is_private_url(), Docling adapter for document parsing., Async variant - runs sync parse in a thread., Parse multiple documents using Docling's batch conversion., Convert ParsedDocument to LangChain Document objects. (+33 more)

### Community 3 - "Types Parseddocument"
Cohesion: 0.06
Nodes (47): Shared test fixtures., Reset the plugin registry before each test., Mock parser for testing., Mock extractor for testing., IngestionError, Raised when vector ingestion fails., BaseExtractor protocol for structured data extraction., Protocol that all structured extractors must implement. (+39 more)

### Community 4 - "Rag Pipeline Ragpipeline"
Cohesion: 0.05
Nodes (56): CHANGELOG v0.1.0 - Core Architecture, CHANGELOG v0.2.0 - RAG Pipeline + Eval, CHANGELOG v0.3.0 - Contextual Injection + Cache + Streaming + Auto RAG, CHANGELOG v0.4.1 - Bug Fixes (LangExtract + Hybrid), CLAUDE.md: Key File Map, CLI evaluate run Command, CLI rag query Command, CLI serve Command (+48 more)

### Community 5 - "Test Rag"
Cohesion: 0.06
Nodes (23): MockExtractor, MockParser, Shared Test Fixtures (conftest.py), Core Errors (docpipe.core.errors), Core Pipeline Orchestrator (docpipe.core.pipeline), Core Types (docpipe.core.types), GLMOCRParser (docpipe.parsers.glm_ocr_parser), PluginRegistry (+15 more)

### Community 6 - "Test Eval"
Cohesion: 0.06
Nodes (41): Eval Pipeline (docpipe.eval.pipeline), RAG Pipeline (docpipe.rag.pipeline), cmd_build(), cmd_lint(), cmd_release(), cmd_serve(), cmd_test(), run.py Ops Script (+33 more)

### Community 7 - "Core Errors Docpipeerror"
Cohesion: 0.06
Nodes (50): docpipe __version__ (0.4.5), load_config() — YAML + Env Config Loader, DocpipeSettings — Pydantic Settings (DOCPIPE_* env prefix), allow_private_urls — SSRF Bypass for Docker Networks, auth_enabled — HTTP Basic Auth Toggle, ConfigurationError, DocpipeError — Base Exception, EvalError (+42 more)

### Community 8 - "Test Improvements"
Cohesion: 0.12
Nodes (22): _make_ingest_config(), _make_rag_config(), _make_rag_result(), test_auto_dispatches_each_valid_strategy(), test_auto_dispatches_to_chosen_strategy(), test_auto_falls_back_to_naive_on_invalid_response(), test_auto_metadata_contains_strategy(), test_cache_evicts_oldest_when_full() (+14 more)

### Community 9 - "Conftest Mockparser"
Cohesion: 0.12
Nodes (6): mock_extractor(), mock_parser(), MockExtractor, MockParser, _reset_registry(), TestPipeline

### Community 10 - "Pipeline"
Cohesion: 0.12
Nodes (11): _compute_hit_rate(), _compute_mrr(), _compute_source_hash(), _cosine_sim(), _create_context_llm(), _create_embeddings(), create_llm(), _create_splitter() (+3 more)

### Community 11 - "Test Metadata Filtering"
Cohesion: 0.12
Nodes (15): Ingestion Pipeline (docpipe.ingestion.pipeline), _make_config(), _make_extractions(), _make_parsed_doc(), test_extractions_to_lc_docs(), test_parsed_to_lc_docs(), Tests for metadata filtering support in RAG query, stream, and search endpoints., RAGConfig should have a filters field with a default of empty dict. (+7 more)

### Community 12 - "Test Config"
Cohesion: 0.12
Nodes (12): BaseSettings, Config Loader (docpipe.config.loader), DocpipeSettings (docpipe.config.settings), load_config(), _load_yaml(), YAML and environment-based configuration loader., Load configuration from YAML file, env vars, or defaults.      Priority (highest, Load and parse a YAML config file. (+4 more)

### Community 13 - "Pipeline Ragpipeline Rerank"
Cohesion: 0.32
Nodes (0): 

### Community 14 - "Ingestion Pipeline Contextual Injection"
Cohesion: 0.4
Nodes (5): Contextual Chunk Injection (LLM Situational Context), Incremental Ingestion (Source Hash Deduplication), IngestionPipeline.ingest() — Main Ingestion Method, Rationale: contextual_injection prepends LLM-generated situational context to each chunk to improve RAG retrieval fidelity, Rationale: incremental mode uses SHA-256 of file bytes to skip unchanged sources and avoid re-embedding

### Community 15 - "Auth"
Cohesion: 0.5
Nodes (3): HTTP Basic Auth dependency for docpipe server., FastAPI dependency — enforces Basic Auth when auth is enabled.      Skipped enti, require_auth()

### Community 16 - "Homepage"
Cohesion: 0.67
Nodes (1): Homepage HTML for the docpipe web UI.

### Community 17 - "Core Types Ragchunk"
Cohesion: 1.0
Nodes (2): RAGChunk — Retrieved Chunk with Provenance, RAGResult — RAG Query Output

### Community 18 - "Core Types Evalmetrics"
Cohesion: 1.0
Nodes (2): EvalMetrics — Aggregate Evaluation Metrics, EvalResult — Evaluation Pipeline Output

### Community 19 - "Version"
Cohesion: 1.0
Nodes (0): 

### Community 20 - "Init Convenience Extract"
Cohesion: 1.0
Nodes (1): extract() — Convenience Function

### Community 21 - "Init Convenience Rag"
Cohesion: 1.0
Nodes (1): rag() — RAG Convenience Function

### Community 22 - "Init Convenience Stream Query"
Cohesion: 1.0
Nodes (1): stream_query() — Streaming RAG Convenience Function

### Community 23 - "Ingestion Pipeline Llm Providers"
Cohesion: 1.0
Nodes (1): LLM_PROVIDERS — Contextual Injection LLM Registry

### Community 24 - "Ingestion Pipeline Contextual Injection Prompt"
Cohesion: 1.0
Nodes (1): CONTEXTUAL_INJECTION_PROMPT — LLM Context Prompt Template

### Community 25 - "Core Types Deleterequest"
Cohesion: 1.0
Nodes (1): DeleteRequest — Vector Store Deletion Request

### Community 26 - "Core Types Deleteresponse"
Cohesion: 1.0
Nodes (1): DeleteResponse — Deletion Operation Result

### Community 27 - "Server App Parse Request"
Cohesion: 1.0
Nodes (1): ParseRequest Model

### Community 28 - "Server App Extract Request"
Cohesion: 1.0
Nodes (1): ExtractRequest Model

### Community 29 - "Server App Ingest Request"
Cohesion: 1.0
Nodes (1): IngestRequest Model

### Community 30 - "Server App Search Request"
Cohesion: 1.0
Nodes (1): SearchRequest Model

### Community 31 - "Server App Evaluate Request"
Cohesion: 1.0
Nodes (1): EvaluateRequest Model

### Community 32 - "Server App Generate Request"
Cohesion: 1.0
Nodes (1): GenerateRequest Model

### Community 33 - "Cli Main Cli Group"
Cohesion: 1.0
Nodes (1): CLI Click Group Entry Point

### Community 34 - "Cli Main Cmd Run"
Cohesion: 1.0
Nodes (1): CLI run Command (parse+extract)

### Community 35 - "Cli Main Cmd Search"
Cohesion: 1.0
Nodes (1): CLI search Command

### Community 36 - "Cli Main Cmd Config Init"
Cohesion: 1.0
Nodes (1): CLI config init Command

### Community 37 - "Changelog V021"
Cohesion: 1.0
Nodes (1): CHANGELOG v0.2.1 - PyPI + Landing Page

### Community 38 - "Changelog V040"
Cohesion: 1.0
Nodes (1): CHANGELOG v0.4.0 - GLM-OCR Parser

### Community 39 - "Changelog V042"
Cohesion: 1.0
Nodes (1): CHANGELOG v0.4.2 - Docker + Anthropic + Auto strategy docs

## Knowledge Gaps
- **126 isolated node(s):** `Bump version, commit, tag. Push with: git push origin main --tags`, `Run ruff check + format check.`, `Start docpipe FastAPI server.`, `Unit tests for POST /rag/stream SSE endpoint.`, `Endpoint returns 200 with text/event-stream content type and SSE tokens.` (+121 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Core Types Ragchunk`** (2 nodes): `RAGChunk — Retrieved Chunk with Provenance`, `RAGResult — RAG Query Output`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Core Types Evalmetrics`** (2 nodes): `EvalMetrics — Aggregate Evaluation Metrics`, `EvalResult — Evaluation Pipeline Output`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Version`** (1 nodes): `_version.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Init Convenience Extract`** (1 nodes): `extract() — Convenience Function`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Init Convenience Rag`** (1 nodes): `rag() — RAG Convenience Function`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Init Convenience Stream Query`** (1 nodes): `stream_query() — Streaming RAG Convenience Function`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Ingestion Pipeline Llm Providers`** (1 nodes): `LLM_PROVIDERS — Contextual Injection LLM Registry`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Ingestion Pipeline Contextual Injection Prompt`** (1 nodes): `CONTEXTUAL_INJECTION_PROMPT — LLM Context Prompt Template`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Core Types Deleterequest`** (1 nodes): `DeleteRequest — Vector Store Deletion Request`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Core Types Deleteresponse`** (1 nodes): `DeleteResponse — Deletion Operation Result`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Server App Parse Request`** (1 nodes): `ParseRequest Model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Server App Extract Request`** (1 nodes): `ExtractRequest Model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Server App Ingest Request`** (1 nodes): `IngestRequest Model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Server App Search Request`** (1 nodes): `SearchRequest Model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Server App Evaluate Request`** (1 nodes): `EvaluateRequest Model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Server App Generate Request`** (1 nodes): `GenerateRequest Model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Cli Main Cli Group`** (1 nodes): `CLI Click Group Entry Point`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Cli Main Cmd Run`** (1 nodes): `CLI run Command (parse+extract)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Cli Main Cmd Search`** (1 nodes): `CLI search Command`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Cli Main Cmd Config Init`** (1 nodes): `CLI config init Command`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Changelog V021`** (1 nodes): `CHANGELOG v0.2.1 - PyPI + Landing Page`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Changelog V040`** (1 nodes): `CHANGELOG v0.4.0 - GLM-OCR Parser`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Changelog V042`** (1 nodes): `CHANGELOG v0.4.2 - Docker + Anthropic + Auto strategy docs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PluginRegistry` connect `Registry Pluginregistry` to `Pipeline Ragpipeline`, `Types Documentformat`, `Types Parseddocument`, `Rag Pipeline Ragpipeline`, `Test Rag`, `Conftest Mockparser`?**
  _High betweenness centrality (0.227) - this node is a cross-community bridge._
- **Why does `Register built-in parsers and extractors if their dependencies are available.` connect `Registry Pluginregistry` to `Pipeline Ragpipeline`, `Types Documentformat`, `Types Parseddocument`, `Core Errors Docpipeerror`?**
  _High betweenness centrality (0.131) - this node is a cross-community bridge._
- **Why does `_register_builtins()` connect `Core Errors Docpipeerror` to `Registry Pluginregistry`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Are the 71 inferred relationships involving `PluginRegistry` (e.g. with `MockParser` and `MockExtractor`) actually correct?**
  _`PluginRegistry` has 71 INFERRED edges - model-reasoned connections that need verification._
- **Are the 66 inferred relationships involving `RAGPipeline` (e.g. with `TestContextualInjection` and `TestSemanticQueryCache`) actually correct?**
  _`RAGPipeline` has 66 INFERRED edges - model-reasoned connections that need verification._
- **Are the 82 inferred relationships involving `ParsedDocument` (e.g. with `MockParser` and `MockExtractor`) actually correct?**
  _`ParsedDocument` has 82 INFERRED edges - model-reasoned connections that need verification._
- **Are the 81 inferred relationships involving `ExtractionSchema` (e.g. with `MockParser` and `MockExtractor`) actually correct?**
  _`ExtractionSchema` has 81 INFERRED edges - model-reasoned connections that need verification._