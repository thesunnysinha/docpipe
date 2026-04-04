# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/thesunnysinha/docpipe/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/thesunnysinha/docpipe/releases/tag/v0.1.0
