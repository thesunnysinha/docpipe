# Docpipe Plugin Foundation Implementation Plan

## Purpose

Implement the approved plugin-foundation architecture without changing supported SDK, CLI, or HTTP behavior. Milestone one establishes the contracts and migrates pgvector, TurboVec, local files, and HTTP sources. Milestone two adds Qdrant and S3/MinIO to prove that new integrations require no changes to core control flow.

Design source: `docs/superpowers/specs/2026-09-13-plugin-foundation-design.md`.

## Delivery strategy

Deliver the work as small, independently reviewable pull requests. Each PR must keep the repository green, preserve backward compatibility, and avoid combining structural migration with unrelated features.

Recommended PR sequence:

1. Architecture guardrails and baselines.
2. Plugin domain models, errors, redaction, and configuration.
3. Catalog, manifest discovery, policy, loading, and lifecycle.
4. Composition roots and registry compatibility facade.
5. Vector contracts and embedding boundary.
6. pgvector adapter.
7. TurboVec adapter.
8. Ingestion decomposition and vector migration.
9. RAG decomposition and vector migration.
10. Source contracts and local resolver.
11. HTTP resolver and parser-input compatibility.
12. Discovery API, public test kit, documentation, and final compatibility gate.
13. Qdrant reference plugin.
14. S3/MinIO reference plugin.

Do not start Qdrant or S3 work until milestone-one acceptance criteria pass.

## Working rules for every task

- Write or update the focused test first and observe the expected failure.
- Implement the smallest cohesive production change that makes the test pass.
- Run the focused unit tests, then Ruff and mypy on changed modules.
- Run `git diff --check` before each commit.
- Use complete public docstrings. Document arguments, return values, public exceptions, side effects, lifecycle ownership, concurrency, and credential handling where relevant.
- Add comments only for invariants, security decisions, vendor limitations, or non-obvious lifecycle behavior.
- Do not import vendor packages from contracts, coordinators, schemas, or composition-independent modules.
- Do not introduce new `Any` annotations in plugin contracts or application coordinators.
- Do not add dependencies to the base `dependencies` list.
- Do not expand an oversized existing module. Extract the responsibility being changed.
- Prefer one production responsibility and its tests per commit.

## Quality commands

Use the project virtual environment:

```bash
.venv/bin/python -m pytest tests/unit/ -q
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src/docpipe/ --ignore-missing-imports
git diff --check
```

Run relevant integration tests after adapter changes and the full suite at each PR boundary:

```bash
.venv/bin/python -m pytest
```

## Milestone one

### Task 1: Establish architecture and size gates

**Create**

- `scripts/check_architecture.py`
- `tests/architecture/test_dependency_boundaries.py`
- `tests/architecture/test_module_sizes.py`
- `docs/architecture/decisions/0001-plugin-boundaries.md`

**Modify**

- `pyproject.toml`
- `.github/workflows/ci.yml`
- `CONTRIBUTING.md`

**Test first**

1. Add a test that records current oversized production modules as an explicit baseline.
2. Add a fixture module that violates an import boundary and verify the checker reports the exact dependency edge.
3. Add fixtures at 250, 300, and 351 logical lines and verify advisory and failure behavior.
4. Verify `__init__.py` business logic is detected without rejecting ordinary re-exports.

**Implementation**

1. Count logical source lines through Python tokenization or AST parsing rather than raw `wc -l`.
2. Enforce these dependency rules:
   - Plugin contracts cannot import adapters, server, CLI, LangChain, or vendor SDKs.
   - Application coordinators cannot import server, CLI, or concrete adapters.
   - Server and CLI may import composition roots and application services.
   - Adapters may import contracts and domain models.
3. Record grandfathered oversized modules with their exact logical-line baseline. Reject growth above that baseline.
4. Warn above 250 lines, require an ADR above 300, and fail new production modules above 350 lines.
5. Add Ruff complexity settings for new code. Use per-file exceptions only for grandfathered modules and document each exception.
6. Add architecture tests to CI before implementation begins so later tasks cannot erode boundaries.
7. Document how to split by responsibility rather than mechanically splitting by line count.

**Verification**

```bash
.venv/bin/python -m pytest tests/architecture/ -q
.venv/bin/ruff check scripts/check_architecture.py tests/architecture/
.venv/bin/mypy scripts/check_architecture.py --ignore-missing-imports
```

**Commit**

```text
test: enforce architecture and module size boundaries
```

### Task 2: Define plugin primitives and stable errors

**Create**

- `src/docpipe/plugins/__init__.py`
- `src/docpipe/plugins/api_version.py`
- `src/docpipe/plugins/descriptors.py`
- `src/docpipe/plugins/errors.py`
- `src/docpipe/plugins/configuration.py`
- `src/docpipe/plugins/credentials.py`
- `src/docpipe/plugins/redaction.py`
- `tests/unit/plugins/test_descriptors.py`
- `tests/unit/plugins/test_configuration.py`
- `tests/unit/plugins/test_credentials.py`
- `tests/unit/plugins/test_redaction.py`
- `tests/unit/plugins/test_errors.py`

**Test first**

1. Verify immutable descriptors reject invalid names, unknown categories, invalid API ranges, and capability duplicates.
2. Verify recursive JSON configuration accepts JSON primitives only and rejects Python objects.
3. Verify provider configuration rejects unknown keys with a precise field path.
4. Verify `SecretStr` and secret references never expose values through `repr`, string conversion, model dumps, or validation errors.
5. Verify recursive redaction covers mapping keys, nested sequences, authorization headers, DSNs, and signed-URL query parameters.
6. Verify public errors expose stable codes, safe context, retry classification, and causal chaining.
7. Verify error serialization cannot include raw configuration or vendor exception text unless it passes redaction.

**Implementation**

1. Define `DOCPIPE_PLUGIN_API_VERSION` and a tested semantic-version range parser.
2. Define immutable `PluginDescriptor`, `PluginCategory`, `PluginStability`, `PluginRequirement`, and runtime requirement models.
3. Define recursive `JSONValue` without `Any`.
4. Define `PluginConfig` for transport and a generic typed factory configuration boundary.
5. Define `SecretReference` and `CredentialResolver` protocol. Include environment and file resolvers only if already needed; do not add cloud secret-manager dependencies.
6. Define `RetryClassification`: `never`, `transient`, `throttled`, and `unknown`.
7. Add the plugin, source, and vector error hierarchies from the design.
8. Make redaction pure, recursive, bounded by depth, and safe for malformed values.
9. Export only intentional public types from `plugins/__init__.py`; keep the file declarative.

**Logging requirement**

Do not log inside value models. Errors carry safe fields; orchestration boundaries decide when to log.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/plugins/test_descriptors.py tests/unit/plugins/test_configuration.py tests/unit/plugins/test_credentials.py tests/unit/plugins/test_redaction.py tests/unit/plugins/test_errors.py -q
.venv/bin/ruff check src/docpipe/plugins tests/unit/plugins
.venv/bin/mypy src/docpipe/plugins --strict --ignore-missing-imports
```

**Commit**

```text
feat: add typed plugin primitives and safe errors
```

### Task 3: Build immutable catalog, static manifest discovery, and policy

**Create**

- `src/docpipe/plugins/catalog.py`
- `src/docpipe/plugins/discovery.py`
- `src/docpipe/plugins/policy.py`
- `src/docpipe/plugins/manifest.schema.json`
- `tests/unit/plugins/test_catalog.py`
- `tests/unit/plugins/test_discovery.py`
- `tests/unit/plugins/test_policy.py`
- `tests/fixtures/plugins/`

**Test first**

1. Verify catalog construction is mutable only inside a builder and immutable after `build()`.
2. Verify separate catalogs do not share state and can run concurrently in tests.
3. Verify discovery enumerates entry-point and distribution metadata without importing plugin modules.
4. Verify valid `docpipe-plugin.json` manifests become descriptors.
5. Verify absent manifests produce basic unloaded descriptors.
6. Verify malformed manifests isolate the failure to one distribution.
7. Verify duplicate third-party names fail deterministically and official built-ins cannot be silently replaced.
8. Verify API-incompatible plugins remain visible as unavailable and are never imported.
9. Verify category allowlists, global denylists, and tenant policy produce deterministic decisions.

**Implementation**

1. Define `PluginRegistration` containing category, name, distribution, import target, descriptor, and origin.
2. Implement `PluginCatalogBuilder`; return an immutable `PluginCatalog` with stable sorted iteration.
3. Read static plugin manifests from distribution metadata and validate against the checked-in JSON Schema.
4. Register official built-ins from static checked-in descriptors rather than importing implementation modules.
5. Implement explicit collision policy and errors.
6. Implement process and tenant plugin policy as pure decision functions.
7. Log one safe warning per invalid or incompatible plugin, not one warning per request.

**Structured events**

- `plugin.discovery.started`
- `plugin.discovery.completed`
- `plugin.manifest.invalid`
- `plugin.registration.conflict`

Include duration, distribution, plugin name/category, outcome, and safe error code. Do not include filesystem installation paths in API responses.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/plugins/test_catalog.py tests/unit/plugins/test_discovery.py tests/unit/plugins/test_policy.py -q
.venv/bin/ruff check src/docpipe/plugins tests/unit/plugins
.venv/bin/mypy src/docpipe/plugins --strict --ignore-missing-imports
```

**Commit**

```text
feat: add immutable plugin catalog and manifest discovery
```

### Task 4: Implement loader, scoped runtime, and bounded blocking runner

**Create**

- `src/docpipe/plugins/loader.py`
- `src/docpipe/plugins/lifecycle.py`
- `src/docpipe/core/operation.py`
- `src/docpipe/core/blocking.py`
- `tests/unit/plugins/test_loader.py`
- `tests/unit/plugins/test_lifecycle.py`
- `tests/unit/core/test_blocking.py`
- `tests/unit/core/test_operation.py`

**Test first**

1. Verify loading occurs only after catalog selection and policy approval.
2. Verify missing dependencies become `PluginDependencyError` with the declared installation hint.
3. Verify constructor failures are translated without exposing secrets.
4. Verify operation-, request-, and process-scoped instances have the documented reuse behavior.
5. Verify asynchronous and synchronous context-managed resources close exactly once, including cancellation and partial construction failures.
6. Verify bounded blocking execution never exceeds configured concurrency.
7. Verify deadlines expire with stable error classification and cancellation propagates where the underlying operation permits it.

**Implementation**

1. Implement `PluginLoader` with lazy `importlib` loading and API compatibility revalidation.
2. Define generic, typed factory protocols; do not return `Any`.
3. Implement `PluginRuntime` around `AsyncExitStack` with explicit scope ownership.
4. Define immutable `OperationContext` with request ID, trace context, opaque tenant ID, deadline, and optional idempotency key.
5. Implement one bounded blocking runner used by all synchronous adapters.
6. Document that cancelling an await does not terminate an already-running Python thread; bound its resources and discard late results safely.

**Structured events**

- `plugin.load.started`
- `plugin.load.completed`
- `plugin.load.failed`
- `plugin.instance.closed`
- `operation.deadline.exceeded`

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/plugins/test_loader.py tests/unit/plugins/test_lifecycle.py tests/unit/core/test_blocking.py tests/unit/core/test_operation.py -q
.venv/bin/ruff check src/docpipe/plugins src/docpipe/core tests/unit/plugins tests/unit/core
.venv/bin/mypy src/docpipe/plugins src/docpipe/core --strict --ignore-missing-imports
```

**Commit**

```text
feat: add lazy plugin loading and scoped lifecycle
```

### Task 5: Add composition roots and isolate the legacy registry

**Create**

- `src/docpipe/bootstrap/__init__.py`
- `src/docpipe/bootstrap/runtime.py`
- `src/docpipe/bootstrap/sdk.py`
- `src/docpipe/bootstrap/server.py`
- `tests/unit/bootstrap/test_runtime.py`
- `tests/unit/bootstrap/test_composition.py`

**Modify**

- `src/docpipe/registry/registry.py`
- `src/docpipe/server/app.py`
- `src/docpipe/server/deps.py`
- `src/docpipe/config/__init__.py`
- `tests/conftest.py`
- `tests/unit/test_registry.py`

**Test first**

1. Verify two application runtimes contain isolated catalogs, settings, and lifecycles.
2. Verify FastAPI lifespan creates and closes one application-scoped runtime.
3. Verify dependencies read runtime objects from app state rather than process globals.
4. Verify SDK composition accepts explicit settings and test doubles.
5. Verify existing `PluginRegistry.get()` behavior still works through a deprecated compatibility facade.
6. Verify new bootstrap and coordinator modules contain no calls to `PluginRegistry.get()` or `get_settings()`.

**Implementation**

1. Define `DocpipeRuntime` containing settings, catalog, loader, plugin runtime, blocking runner, and future service ports.
2. Build explicit SDK and server composition functions.
3. Store the server runtime in FastAPI application state and close it during lifespan shutdown.
4. Convert `PluginRegistry` into a thin compatibility facade over the default SDK runtime.
5. Add one-per-process deprecation warnings only where public legacy APIs require them; do not warn internal callers.
6. Replace global-reset test fixtures with isolated runtime fixtures for new tests.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/bootstrap tests/unit/test_registry.py tests/unit/server/api -q
.venv/bin/ruff check src/docpipe/bootstrap src/docpipe/registry src/docpipe/server tests/unit/bootstrap
.venv/bin/mypy src/docpipe/bootstrap src/docpipe/registry src/docpipe/server --ignore-missing-imports
```

**Commit**

```text
refactor: introduce explicit application composition roots
```

### Task 6: Define vector domain models, embedding port, and facet contracts

**Create**

- `src/docpipe/plugins/contracts/vectorstore/__init__.py`
- `src/docpipe/plugins/contracts/vectorstore/models.py`
- `src/docpipe/plugins/contracts/vectorstore/capabilities.py`
- `src/docpipe/plugins/contracts/vectorstore/reader.py`
- `src/docpipe/plugins/contracts/vectorstore/writer.py`
- `src/docpipe/plugins/contracts/vectorstore/admin.py`
- `src/docpipe/embeddings/__init__.py`
- `src/docpipe/embeddings/contracts.py`
- `src/docpipe/embeddings/langchain_adapter.py`
- `src/docpipe/testing/__init__.py`
- `src/docpipe/testing/vectorstores.py`
- `tests/unit/vectorstores/test_models.py`
- `tests/unit/vectorstores/test_contracts.py`
- `tests/unit/embeddings/test_langchain_adapter.py`

**Test first**

1. Verify immutable records normalize IDs, text, vectors, and JSON metadata.
2. Verify invalid vectors, non-finite floats, invalid collection names, and unsupported metadata values fail early.
3. Verify typed filter expressions support equality, membership, ranges, boolean composition, and explicit rejection of raw vendor syntax.
4. Verify `VectorQuery` distinguishes dense, sparse, and hybrid forms.
5. Verify `WriteBatchResult` cannot report inconsistent accepted/rejected/uncertain counts.
6. Verify `VectorStoreBinding` matches its advertised facets.
7. Verify structural test doubles satisfy the narrow protocols without inheriting Docpipe classes.
8. Verify the LangChain embedding adapter returns plain vectors and never exposes LangChain types.
9. Verify the public conformance kit can be imported from an installed wheel layout.

**Implementation**

1. Define Docpipe-owned immutable models: `VectorRecord`, `VectorQuery`, `VectorMatch`, `CollectionRef`, `SourceAggregate`, `WriteBatch`, `WriteBatchResult`, and typed filter nodes.
2. Define versioned vector capability enum values.
3. Define asynchronous structural protocols: `VectorReader`, `VectorWriter`, `VectorCollectionAdmin`, and `PluginHealthProbe`.
4. Define `VectorStoreBinding` as a typed group of optional facets with no business methods.
5. Define internal `EmbeddingEncoder` and adapt existing LangChain embedding objects behind it.
6. Publish reusable conformance assertions in `docpipe.testing.vectorstores` without depending on repository test modules.
7. Keep every contract module focused and below the architecture threshold.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/vectorstores/test_models.py tests/unit/vectorstores/test_contracts.py tests/unit/embeddings -q
.venv/bin/ruff check src/docpipe/plugins/contracts src/docpipe/embeddings src/docpipe/testing tests/unit/vectorstores tests/unit/embeddings
.venv/bin/mypy src/docpipe/plugins/contracts src/docpipe/embeddings src/docpipe/testing --strict --ignore-missing-imports
```

**Commit**

```text
feat: define vector store facets and embedding boundary
```

### Task 7: Implement the pgvector adapter

**Create**

- `src/docpipe/vectorstores/pgvector/__init__.py`
- `src/docpipe/vectorstores/pgvector/configuration.py`
- `src/docpipe/vectorstores/pgvector/adapter.py`
- `src/docpipe/vectorstores/pgvector/filters.py`
- `src/docpipe/vectorstores/pgvector/queries.py`
- `tests/unit/vectorstores/pgvector/test_configuration.py`
- `tests/unit/vectorstores/pgvector/test_filters.py`
- `tests/unit/vectorstores/pgvector/test_adapter.py`
- `tests/integration/vectorstores/test_pgvector_contract.py`

**Modify**

- `pyproject.toml`

**Test first**

1. Instantiate the public vector conformance suite for pgvector.
2. Verify configuration accepts legacy DSNs only at the compatibility boundary and stores them as secrets internally.
3. Verify collection names are validated or safely quoted.
4. Verify every filter node compiles to parameterized SQL or a safe supported client expression.
5. Verify dense search, metadata filters, deterministic upsert, exact delete, source aggregation, and health behavior.
6. Verify connection errors and missing schema errors map to stable Docpipe exceptions.
7. Verify partial failures and transaction boundaries are reported accurately.
8. Verify logs do not contain DSNs, queries with values, content, or vectors.

**Implementation**

1. Wrap `langchain-postgres` only where it offers correct semantics; use a narrow repository helper for operations it cannot express safely.
2. Remove interpolated identifiers from public-input paths. Validate and quote identifiers through one helper.
3. Compile Docpipe filter expressions in `filters.py`.
4. Keep SQL statements and row mapping in `queries.py`, lifecycle and exception translation in `adapter.py`, and validation in `configuration.py`.
5. Use deterministic record IDs and transactions where supported.
6. Register the static built-in descriptor and entry point without importing the adapter during discovery.

**Structured events**

- `vectorstore.upsert.*`
- `vectorstore.search.*`
- `vectorstore.delete.*`
- `vectorstore.collection.*`
- `vectorstore.health.*`

Use bounded-cardinality fields only.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/vectorstores/pgvector -q
.venv/bin/python -m pytest tests/integration/vectorstores/test_pgvector_contract.py -q
.venv/bin/ruff check src/docpipe/vectorstores/pgvector tests/unit/vectorstores/pgvector tests/integration/vectorstores
.venv/bin/mypy src/docpipe/vectorstores/pgvector --strict --ignore-missing-imports
```

**Commit**

```text
feat: add pgvector plugin adapter
```

### Task 8: Implement the TurboVec adapter

**Create**

- `src/docpipe/vectorstores/turbovec/__init__.py`
- `src/docpipe/vectorstores/turbovec/configuration.py`
- `src/docpipe/vectorstores/turbovec/adapter.py`
- `src/docpipe/vectorstores/turbovec/persistence.py`
- `tests/unit/vectorstores/turbovec/test_configuration.py`
- `tests/unit/vectorstores/turbovec/test_persistence.py`
- `tests/unit/vectorstores/turbovec/test_adapter.py`
- `tests/integration/vectorstores/test_turbovec_contract.py`

**Modify**

- `src/docpipe/vectorstores/turbovec_store.py`
- `pyproject.toml`

**Test first**

1. Instantiate applicable vector conformance tests for TurboVec.
2. Verify unsupported facets and capabilities are explicit.
3. Verify index paths cannot escape the configured root through collection names.
4. Verify atomic persistence uses a temporary sibling plus replace, preserving the prior index after failure.
5. Verify concurrent writes are serialized or rejected predictably.
6. Verify corrupt index and malformed docstore errors are translated safely.
7. Verify deterministic delete and source aggregation behavior.
8. Verify no model, index, or vendor object loads during discovery.

**Implementation**

1. Move persistence parsing and atomic writes to `persistence.py`.
2. Put vendor imports and exception translation in `adapter.py`.
3. Validate bit width, index root, collection name, and filesystem permissions in configuration.
4. Use the shared bounded blocking runner for synchronous vendor operations.
5. Keep `turbovec_store.py` as a deprecated compatibility facade until internal callers migrate.
6. Register the built-in descriptor and entry point.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/vectorstores/turbovec tests/integration/vectorstores/test_turbovec_contract.py -q
.venv/bin/ruff check src/docpipe/vectorstores/turbovec tests/unit/vectorstores/turbovec
.venv/bin/mypy src/docpipe/vectorstores/turbovec --strict --ignore-missing-imports
```

**Commit**

```text
feat: add turbovec plugin adapter
```

### Task 9: Decompose ingestion and migrate it to vector facets

**Create**

- `src/docpipe/ingestion/coordinator.py`
- `src/docpipe/ingestion/document_builder.py`
- `src/docpipe/ingestion/incremental.py`
- `src/docpipe/ingestion/contextualization.py`
- `src/docpipe/ingestion/configuration.py`
- `tests/unit/ingestion/test_coordinator.py`
- `tests/unit/ingestion/test_document_builder.py`
- `tests/unit/ingestion/test_incremental.py`
- `tests/unit/ingestion/test_contextualization.py`
- `tests/compat/test_ingestion_legacy.py`

**Modify**

- `src/docpipe/ingestion/pipeline.py`
- `src/docpipe/vectorstores/factory.py`
- `src/docpipe/core/types.py`
- `src/docpipe/server/request_mapping.py`
- `tests/unit/test_ingestion.py`
- `tests/unit/test_vector_backend.py`

**Test first**

1. Snapshot supported legacy ingestion results and errors through SDK and HTTP paths.
2. Verify coordinator sequencing using narrow chunker, encoder, writer, and administration test doubles.
3. Verify document construction produces Docpipe records rather than LangChain documents.
4. Verify content fingerprints use bytes and deterministic metadata.
5. Verify incremental-state lookup failures fail closed by default.
6. Verify explicit legacy best-effort mode preserves old fail-open behavior with a warning.
7. Verify batches respect configured size and in-flight bounds.
8. Verify partial and uncertain writes propagate to a failed or explicit partial result; they cannot return a normal completed response.
9. Verify cancellation closes acquired resources.

**Implementation**

1. Move parsed/extraction normalization to `document_builder.py`.
2. Move fingerprinting and duplicate decisions to `incremental.py`.
3. Move contextual injection to `contextualization.py` behind a narrow interface.
4. Implement `IngestionCoordinator` with injected chunker, encoder, vector facets, logger/tracer boundary, and limits.
5. Keep `IngestionPipeline` as a compatibility facade that delegates to a runtime-created coordinator.
6. Stop passing LangChain documents to vector stores. Convert at the chunker or legacy adapter boundary only.
7. Stop reading global settings inside ingestion methods.
8. Reduce `ingestion/pipeline.py` toward a facade-sized module; it must not exceed its baseline at any intermediate commit.
9. Convert `vectorstores/factory.py` into a compatibility facade and remove internal imports when callers are migrated.

**Structured events**

- `ingestion.started`
- `ingestion.chunking.completed`
- `ingestion.embedding.completed`
- `ingestion.write.completed`
- `ingestion.partial`
- `ingestion.failed`

Log counts and durations, never content, metadata payloads, vectors, DSNs, or source URLs.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/ingestion tests/compat/test_ingestion_legacy.py tests/unit/test_ingestion.py tests/unit/test_vector_backend.py -q
.venv/bin/ruff check src/docpipe/ingestion src/docpipe/vectorstores/factory.py tests/unit/ingestion tests/compat
.venv/bin/mypy src/docpipe/ingestion --strict --ignore-missing-imports
```

**Commit**

```text
refactor: migrate ingestion to vector plugin facets
```

### Task 10: Decompose RAG retrieval and migrate vector access

**Create**

- `src/docpipe/rag/coordinator.py`
- `src/docpipe/rag/generation.py`
- `src/docpipe/rag/retrieval/__init__.py`
- `src/docpipe/rag/retrieval/base.py`
- `src/docpipe/rag/retrieval/registry.py`
- `src/docpipe/rag/retrieval/naive.py`
- `src/docpipe/rag/retrieval/hyde.py`
- `src/docpipe/rag/retrieval/multi_query.py`
- `src/docpipe/rag/retrieval/parent_document.py`
- `src/docpipe/rag/retrieval/hybrid.py`
- `src/docpipe/rag/retrieval/lightrag.py`
- `src/docpipe/rag/retrieval/automatic.py`
- `tests/unit/rag/test_coordinator.py`
- `tests/unit/rag/test_generation.py`
- `tests/unit/rag/retrieval/` with one focused module per strategy
- `tests/compat/test_rag_legacy.py`

**Modify**

- `src/docpipe/rag/pipeline.py`
- `src/docpipe/server/services/rag.py`
- `tests/unit/test_rag.py`
- `tests/unit/test_rag_stream.py`

**Test first**

1. Capture current output, citation, score, token-usage, cache, reranking, and streaming behavior.
2. Test every strategy through a common strategy contract with a fake `VectorReader` and fake encoder.
3. Verify strategy selection is explicit and unknown strategies fail before vendor access.
4. Verify hybrid capability negotiation returns a precise unsupported-capability error.
5. Verify generation and streaming operate independently of retrieval implementation.
6. Verify cache keys include relevant configuration without secrets.
7. Verify cancellation and timeouts close vector and model resources.
8. Verify `rag/pipeline.py` becomes a compatibility facade and contains no backend branches.

**Implementation**

1. Extract generation, token accounting, and stream normalization into `generation.py`.
2. Define a small retrieval strategy protocol in `retrieval/base.py`.
3. Move each existing retrieval strategy into its own cohesive module.
4. Use a data-driven strategy registry rather than an expanding `if`/`elif` chain.
5. Implement `RAGCoordinator` with injected encoder, vector reader, reranker, generator, cache, and strategy registry.
6. Preserve `RAGPipeline` as a public compatibility facade.
7. Inject the coordinator through `RAGService`; remove global settings and concrete vector factory access from new code.
8. Split the existing large test module by strategy and behavior while preserving regression coverage.

**Structured events**

- `rag.query.started`
- `rag.retrieval.completed`
- `rag.rerank.completed`
- `rag.generation.completed`
- `rag.query.failed`

Questions, prompts, retrieved text, and answers are excluded from logs by default. Opt-in content logging is outside this milestone.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/rag tests/compat/test_rag_legacy.py tests/unit/test_rag.py tests/unit/test_rag_stream.py -q
.venv/bin/ruff check src/docpipe/rag tests/unit/rag tests/compat
.venv/bin/mypy src/docpipe/rag --strict --ignore-missing-imports
```

**Commit**

```text
refactor: split rag strategies and inject vector reader
```

### Task 11: Define source handles and implement local resolution

**Create**

- `src/docpipe/plugins/contracts/source/__init__.py`
- `src/docpipe/plugins/contracts/source/models.py`
- `src/docpipe/plugins/contracts/source/handle.py`
- `src/docpipe/plugins/contracts/source/resolver.py`
- `src/docpipe/sources/__init__.py`
- `src/docpipe/sources/local.py`
- `src/docpipe/testing/sources.py`
- `tests/unit/sources/test_models.py`
- `tests/unit/sources/test_handle.py`
- `tests/unit/sources/test_local.py`
- `tests/unit/sources/test_contracts.py`

**Test first**

1. Verify source IDs, display names, content metadata, version tokens, and fingerprints are immutable and normalized.
2. Verify `ResolvedSourceHandle` cleanup runs exactly once after success, exception, and cancellation.
3. Verify `open()` and `materialize()` remain valid only inside the context lifetime.
4. Verify local resolver rejects traversal outside configured roots, unsupported file kinds, symlink escapes, oversized files, and non-regular files.
5. Verify stable content hashing streams data rather than loading an entire file into memory.
6. Verify the public source conformance suite works independently of internal test fixtures.

**Implementation**

1. Define immutable source models and async resolver/handle protocols.
2. Implement a managed handle with explicit ownership and idempotent cleanup.
3. Implement `LocalSourceResolver` with canonicalization, allowed-root policy, size limits, media-type detection, and streaming hash.
4. Add static descriptor, entry point, configuration model, and installation metadata.
5. Keep source logs limited to scheme, safe media type, byte count, duration, and opaque source ID.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/sources -q
.venv/bin/ruff check src/docpipe/plugins/contracts/source src/docpipe/sources src/docpipe/testing/sources.py tests/unit/sources
.venv/bin/mypy src/docpipe/plugins/contracts/source src/docpipe/sources src/docpipe/testing/sources.py --strict --ignore-missing-imports
```

**Commit**

```text
feat: add source resolver contract and local adapter
```

### Task 12: Implement HTTP resolution and parser-input compatibility

**Create**

- `src/docpipe/sources/http.py`
- `src/docpipe/sources/http_security.py`
- `src/docpipe/parsers/input_adapter.py`
- `tests/unit/sources/http/`
- `tests/unit/sources/test_http_security.py`
- `tests/unit/parsers/test_input_adapter.py`
- `tests/compat/test_source_legacy.py`

**Modify**

- `src/docpipe/parsers/url_safety.py`
- `src/docpipe/parsers/router.py`
- `src/docpipe/core/pipeline.py`
- `src/docpipe/server/services/documents.py`
- `src/docpipe/server/services/ingest.py`
- existing parser tests that assume direct URL ownership

**Test first**

1. Instantiate the source conformance suite for HTTP.
2. Verify SSRF protection before connection and after every redirect.
3. Verify DNS rebinding defenses are documented and tested at the connection boundary supported by the HTTP client.
4. Verify timeouts, maximum redirects, content-length checks, streamed byte limits, media types, and temporary-file permissions.
5. Verify signed URLs are completely redacted from logs and errors.
6. Verify path-only legacy parsers receive a managed materialized path.
7. Verify handle-aware parsers may stream without materialization.
8. Verify unchanged third-party parsers still receive their supported input shape.
9. Verify temporary files are removed after parser failure or cancellation.
10. Verify current local-path and HTTP API behavior remains compatible.

**Implementation**

1. Consolidate URL safety policy in `http_security.py`; leave `url_safety.py` as a compatibility facade if public imports exist.
2. Download through the existing HTTP abstraction with bounded streaming and explicit deadlines.
3. Use restricted temporary files under a configured root.
4. Implement `ParserInputAdapter` to materialize only for parsers that require paths.
5. Route document and ingestion services through a selected source resolver.
6. Keep resolver selection based on parsed URI scheme and catalog policy; do not allow arbitrary class names in requests.
7. Preserve original source identity in results while parsers operate on managed local artifacts.

**Structured events**

- `source.resolve.started`
- `source.resolve.completed`
- `source.resolve.failed`
- `source.materialize.completed`
- `source.cleanup.failed`

Cleanup failures are warnings with an opaque handle ID and safe error code. They never expose temporary paths to public responses.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/sources tests/unit/parsers/test_input_adapter.py tests/compat/test_source_legacy.py -q
.venv/bin/python -m pytest tests/unit/server/api tests/unit/test_ingestion.py tests/unit/test_url_safety.py -q
.venv/bin/ruff check src/docpipe/sources src/docpipe/parsers src/docpipe/server/services tests/unit/sources tests/unit/parsers tests/compat
.venv/bin/mypy src/docpipe/sources src/docpipe/parsers/input_adapter.py --strict --ignore-missing-imports
```

**Commit**

```text
feat: route parser inputs through safe source resolvers
```

### Task 13: Add namespaced configuration and legacy translation

**Create**

- `src/docpipe/config/plugin_options.py`
- `src/docpipe/config/compatibility.py`
- `tests/unit/config/test_plugin_options.py`
- `tests/unit/config/compatibility/`

**Modify**

- `src/docpipe/config/settings.py`
- `src/docpipe/core/types.py`
- `src/docpipe/schemas/common.py`
- `src/docpipe/schemas/ingest.py`
- `src/docpipe/schemas/search.py`
- `src/docpipe/schemas/rag.py`
- `src/docpipe/server/request_mapping.py`
- `.env.example`

**Test first**

1. Verify legacy vector and source fields map to exactly equivalent namespaced configuration.
2. Verify agreeing old/new values are accepted and new values take precedence.
3. Verify conflicting old/new values fail with field-specific errors.
4. Verify secret references survive mapping without resolving or serializing their values.
5. Verify unknown provider options fail only after provider selection and include the correct nested path.
6. Verify schemas remain backward compatible and generated OpenAPI documents both paths accurately.
7. Verify deprecation warnings occur once per process, not per record or request.

**Implementation**

1. Add namespaced vector-store and source option envelopes to internal types and HTTP schemas.
2. Isolate legacy translation in pure compatibility functions.
3. Keep provider-specific typed configuration inside plugin packages.
4. Remove the closed `Literal["pgvector", "turbovec"]` from new paths while preserving legacy validation behavior.
5. Mark legacy fields as deprecated in schema metadata only when the support window is documented.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/config tests/unit/test_config.py tests/unit/server/api -q
.venv/bin/ruff check src/docpipe/config src/docpipe/schemas src/docpipe/server/request_mapping.py tests/unit/config
.venv/bin/mypy src/docpipe/config src/docpipe/schemas src/docpipe/server/request_mapping.py --ignore-missing-imports
```

**Commit**

```text
feat: add namespaced plugin configuration with legacy mapping
```

### Task 14: Extend discovery APIs and health reporting

**Create**

- `src/docpipe/schemas/plugin_catalog.py`
- `tests/unit/server/test_plugin_discovery.py`
- `tests/unit/server/test_plugin_health.py`

**Modify**

- `src/docpipe/schemas/plugins.py`
- `src/docpipe/schemas/__init__.py`
- `src/docpipe/server/services/discovery.py`
- `src/docpipe/server/health.py`
- `src/docpipe/profiles/guardrails.py`
- `src/docpipe/server/templates/homepage.html`
- `tests/unit/test_profiles.py`
- `tests/unit/test_health.py`
- `tests/unit/test_homepage.py`

**Test first**

1. Verify `/plugins` returns all categories, capabilities, stability, API compatibility, availability, installation hints, and safe requirements.
2. Verify unavailable and incompatible plugins remain visible without importing their implementation.
3. Verify tenant allowlists affect `allowed` but do not mutate the global catalog.
4. Verify plugin health uses explicit probes with deadlines and does not make `/health` load every optional plugin.
5. Verify no descriptor or health response includes secrets, installation paths, raw exception messages, or class objects.
6. Verify existing parser/extractor response fields remain compatible.

**Implementation**

1. Introduce category-neutral response models without placing all category behavior in one schema file.
2. Map catalog descriptors to API models through a dedicated mapper.
3. Keep health shallow by default; probe only configured active dependencies.
4. Update the homepage with category summaries, not full vendor configuration.
5. Keep service modules thin and injected with catalog/runtime dependencies.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/server/test_plugin_discovery.py tests/unit/server/test_plugin_health.py tests/unit/test_profiles.py tests/unit/test_health.py tests/unit/test_homepage.py -q
.venv/bin/ruff check src/docpipe/schemas src/docpipe/server/services/discovery.py src/docpipe/server/health.py tests/unit/server
.venv/bin/mypy src/docpipe/schemas src/docpipe/server/services/discovery.py src/docpipe/server/health.py --ignore-missing-imports
```

**Commit**

```text
feat: expose safe plugin capabilities and health
```

### Task 15: Publish plugin test kit and documentation

**Create**

- `docs/architecture/plugins.md`
- `docs/architecture/dependency-boundaries.md`
- `docs/plugins/authoring.md`
- `docs/plugins/vectorstores.md`
- `docs/plugins/sources.md`
- `docs/plugins/configuration.md`
- `docs/plugins/security.md`
- `docs/plugins/troubleshooting.md`
- `docs/migrations/plugin-configuration.md`
- `examples/plugin-package/pyproject.toml`
- `examples/plugin-package/src/example_docpipe_plugin/`
- `tests/docs/test_plugin_examples.py`
- `tests/packaging/test_plugin_wheel.py`

**Modify**

- `README.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`
- `pyproject.toml`
- corresponding public documentation in the `docpipe-site` repository

**Test first**

1. Build and install the example plugin wheel in an isolated environment.
2. Verify static discovery works before importing the example module.
3. Run the public conformance kit against the example plugin.
4. Execute documentation snippets that do not require external services.
5. Verify missing-dependency messages reference real extras and commands.
6. Verify public exports exist in both wheel and editable installs.

**Implementation**

1. Document architecture, dependency direction, lifecycle, API versioning, trust, logging, and redaction.
2. Document every public protocol and configuration field with minimal working examples.
3. Include a complete external plugin package rather than only snippets.
4. Document compatibility and removal timelines.
5. Add a capability matrix for built-in vector stores and source resolvers.
6. Update public site documentation in the same release sequence as HTTP or environment changes.

**Verification**

```bash
.venv/bin/python -m pytest tests/docs tests/packaging -q
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
```

**Commit**

```text
docs: publish plugin architecture and authoring guide
```

### Task 16: Complete milestone-one release gate

**Modify**

- `.github/workflows/ci.yml`
- `.github/workflows/docker.yml`
- architecture baseline only if justified by actual decomposition

**Verification sequence**

1. Run the complete test suite.
2. Run Ruff and formatting checks across source and tests.
3. Run mypy with failures blocking for the new plugin, source, embedding, vector-store, ingestion coordinator, and RAG coordinator packages.
4. Run pgvector and TurboVec integration matrices.
5. Build every existing Docker profile and verify image startup without optional unselected dependencies.
6. Build wheel and source distribution and test installation into a fresh environment.
7. Measure import time, process memory, representative ingestion latency, and representative search latency against the recorded baseline.
8. Inspect logs from success, missing dependency, invalid credential, timeout, partial write, and cancellation scenarios for sensitive values.
9. Verify existing HTTP OpenAPI snapshots and SDK compatibility tests.
10. Verify no touched oversized module grew and no new production module exceeds thresholds.
11. Search for concrete backend branches and forbidden globals:

```bash
rg -n "backend ==|backend !=|PluginRegistry\.get\(|get_settings\(\)" src/docpipe/ingestion src/docpipe/rag src/docpipe/server/services
```

Every remaining match must be a documented compatibility facade or unrelated pre-existing path.

**Required result**

- Full tests green on Python 3.10–3.13.
- New strict typing jobs green and no longer `continue-on-error`.
- Architecture gates green.
- Base dependency list unchanged.
- Compatibility matrix documented.
- Rollback switch tested.
- Milestone-one contracts marked `experimental`, ready for reference-plugin validation.

**Commit**

```text
ci: enforce plugin foundation release gates
```

## Milestone two: reference integrations

### Task 17: Add Qdrant without changing core control flow

**Create**

- `src/docpipe/vectorstores/qdrant/__init__.py`
- `src/docpipe/vectorstores/qdrant/schemas.py` (`configuration.py` compatibility export)
- `src/docpipe/vectorstores/qdrant/adapter.py`
- `src/docpipe/vectorstores/qdrant/filters.py`
- `tests/unit/vectorstores/qdrant/`
- `tests/integration/vectorstores/qdrant_spec.py`
- `docs/plugins/qdrant.md`

**Modify**

- `pyproject.toml` to add only the optional `qdrant` extra and entry point
- `.github/workflows/ci.yml` to add an affected-adapter integration job

**Requirements**

1. Begin by instantiating the published vector conformance suite.
2. Implement through existing facets and domain models only.
3. Compile typed filters to Qdrant filter models inside the adapter.
4. Support deterministic point IDs, payload metadata, filtered search, delete-by-source, source aggregation where feasible, health, deadlines, and safe errors.
5. Do not add `qdrant-client` to base or curated profiles until explicitly chosen.
6. Do not change ingestion, RAG, HTTP router, or core contract code. If change is required, stop and review the contract gap before proceeding.
7. Test local Qdrant in CI without production credentials.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/vectorstores/qdrant tests/integration/vectorstores/qdrant_spec.py -q
.venv/bin/ruff check src/docpipe/vectorstores/qdrant tests/unit/vectorstores/qdrant
.venv/bin/mypy src/docpipe/vectorstores/qdrant --strict --ignore-missing-imports
```

**Commit**

```text
feat: add optional qdrant vector store plugin
```

### Task 18: Add S3 and MinIO without changing parser control flow

**Create**

- `src/docpipe/sources/s3/__init__.py`
- `src/docpipe/sources/s3/schemas.py` (`configuration.py` compatibility export)
- `src/docpipe/sources/s3/resolver.py`
- `tests/unit/sources/s3/`
- `tests/integration/sources/minio_spec.py`
- `docs/plugins/s3.md`
- `examples/s3-minio/`

**Modify**

- `pyproject.toml` to add only the optional `s3` extra and entry point
- `.github/workflows/ci.yml` to add a MinIO integration job

**Requirements**

1. Instantiate the published source conformance suite first.
2. Support `s3://` URIs and an optional S3-compatible endpoint.
3. Resolve credentials through `CredentialResolver`; support workload/default credential chains without serializing resolved credentials.
4. Enforce allowed buckets, prefixes, object sizes, timeouts, and endpoint policy.
5. Treat ETag/version ID as a version token and compute a content digest unless trusted-token mode is explicitly configured.
6. Stream downloads and materialize only when requested by the parser input adapter.
7. Test AWS-compatible behavior against MinIO with ephemeral credentials.
8. Do not change parser or ingestion control flow. Contract gaps require design review.

**Verification**

```bash
.venv/bin/python -m pytest tests/unit/sources/s3 tests/integration/sources/minio_spec.py -q
.venv/bin/ruff check src/docpipe/sources/s3 tests/unit/sources/s3
.venv/bin/mypy src/docpipe/sources/s3 --strict --ignore-missing-imports
```

**Commit**

```text
feat: add optional s3 and minio source plugin
```

### Task 19: Stabilize plugin API version 1

**Test and review**

1. Run pgvector, TurboVec, and Qdrant through the same published vector conformance suite.
2. Run local, HTTP, and S3/MinIO through the same published source conformance suite.
3. Build the external example plugin against only documented public APIs.
4. Conduct an API review of contracts, models, exceptions, manifests, and test-kit imports.
5. Confirm no reference integration required backend-specific core changes.
6. Resolve contract ambiguity with additive changes only.
7. Record performance and resource comparisons.
8. Mark plugin API version 1 contracts stable and publish the compatibility policy.

**Commit**

```text
feat: stabilize docpipe plugin api version 1
```

## Deferred roadmap

After plugin API version 1 is stable, plan each category as a separate architectural milestone:

1. Durable job model and orchestration facets, followed by Temporal and Celery adapters.
2. Additional vector plugins: Elasticsearch/OpenSearch, Chroma, Milvus, and Weaviate.
3. Additional source plugins: Azure Blob, GCS, SharePoint, Box, Google Drive, and Notion.
4. Parser/preprocessor plugins: Marker, Tesseract, and OCRmyPDF after license and resource reviews.
5. Provider boundary: generic OpenAI-compatible client, LiteLLM, Ollama, and vLLM interoperability.
6. Observability adapters: Langfuse and Opik through OpenTelemetry-first integration.
7. Graph adapters: Microsoft GraphRAG and graph-store interfaces.
8. External framework packages: LlamaIndex, Haystack, Airflow, Prefect, Dagster, n8n, Dify, and Flowise.

Each category must reuse the same catalog, descriptor, loader, lifecycle, policy, credential, logging, error, API-version, and conformance-test infrastructure. Do not add category-specific behavior to the central catalog.

## Definition of done

The foundation is complete only when all of the following are true:

- Existing consumers pass compatibility tests without code changes.
- pgvector, TurboVec, and Qdrant use the same stable vector facets.
- Local, HTTP, and S3/MinIO use the same stable source contract.
- The base package imports without any optional integration installed.
- Missing integrations produce actionable, safe installation errors.
- All runtime objects are injected; new core code uses no global service locator.
- Contracts and coordinators contain no vendor or LangChain types.
- Resource ownership and cancellation behavior are deterministic.
- Partial writes and uncertain outcomes cannot be reported as success.
- Logs and traces contain stable events and no secrets or document content.
- Public interfaces have complete docstrings and examples.
- Architecture, strict typing, unit, conformance, integration, compatibility, packaging, and security tests pass.
- New modules remain below the architecture thresholds, and affected monoliths are reduced to compatibility facades or cohesive modules.
- Qdrant and S3/MinIO require no core control-flow branches.
- Plugin API version 1 and its compatibility policy are published.
