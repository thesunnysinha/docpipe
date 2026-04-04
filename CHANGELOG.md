# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/thesunnysinha/docpipe/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/thesunnysinha/docpipe/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/thesunnysinha/docpipe/releases/tag/v0.1.0
