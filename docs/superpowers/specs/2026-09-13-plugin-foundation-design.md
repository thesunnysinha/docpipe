# Docpipe Plugin Foundation Design

## Status

Approved design for the first implementation milestone. This specification defines the shared plugin foundation and migration of existing vector-store and source behavior. New Qdrant and S3/MinIO integrations are intentionally deferred to the second milestone so the contracts are proven against current behavior first.

## Objective

Docpipe should support a broad set of independently installable parsers, vector stores, source systems, orchestrators, providers, observability platforms, evaluators, and framework adapters while keeping its base installation small and framework-neutral.

The first milestone establishes stable extension contracts for vector stores and sources. It migrates pgvector, TurboVec, local files, and HTTP sources to those contracts without breaking existing SDK or HTTP API consumers.

## Design principles

1. Optional integrations must not add dependencies to the base installation.
2. Core services depend on Docpipe contracts, never vendor SDK types.
3. Vendor-specific branching remains inside the corresponding adapter.
4. Existing public SDK and HTTP behavior remains compatible throughout the first milestone.
5. Plugin metadata must be discoverable without importing heavyweight SDKs or loading models.
6. Logs, exceptions, descriptors, and persisted metadata must not expose credentials, signed URLs, connection strings, or document contents.
7. Shared conformance tests define observable plugin behavior.
8. Retry policy belongs to the caller or orchestrator; adapters only classify transient failures.
9. Interfaces are segregated by capability; plugins do not implement unrelated no-op methods.
10. Runtime dependencies are supplied explicitly through a composition root. Process-global mutable
    state exists only in a temporary compatibility facade.
11. Docpipe-owned domain models cross plugin boundaries; LangChain and vendor types do not.
12. New modules remain cohesive and small, and existing oversized modules may not grow.

## Scope

### Included

- Vector-store and source contracts.
- Capability descriptors and plugin metadata.
- Entry-point discovery for both plugin categories.
- Typed, namespaced plugin configuration.
- An internal embedding-encoder port that prevents vector backends from depending on LangChain.
- Stable public exception hierarchy.
- Central log-field redaction.
- Structured logging conventions.
- Migration of pgvector and TurboVec.
- Migration of local-file and HTTP source handling.
- Compatibility translation for existing configuration and requests.
- Conformance, unit, integration, security, and compatibility tests.
- Plugin-author and operator documentation.

### Excluded

- Qdrant and S3/MinIO implementations; these are milestone-two reference plugins.
- Temporal, Celery, and a durable job API.
- Additional parsing, OCR, observability, graph, and framework adapters.
- Removal of legacy request or SDK configuration fields.
- A full redesign of existing parser, extractor, chunker, reranker, or evaluator contracts.

## Package layout

```text
src/docpipe/
├── plugins/
│   ├── __init__.py
│   ├── api_version.py
│   ├── catalog.py
│   ├── configuration.py
│   ├── credentials.py
│   ├── descriptors.py
│   ├── discovery.py
│   ├── errors.py
│   ├── lifecycle.py
│   ├── loader.py
│   ├── policy.py
│   ├── redaction.py
│   └── contracts/
│       ├── source/
│       │   ├── handle.py
│       │   ├── models.py
│       │   └── resolver.py
│       └── vectorstore/
│           ├── admin.py
│           ├── capabilities.py
│           ├── models.py
│           ├── reader.py
│           └── writer.py
├── sources/
│   ├── http.py
│   └── local.py
└── vectorstores/
    ├── pgvector/
    │   ├── adapter.py
    │   ├── configuration.py
    │   └── queries.py
    └── turbovec/
        ├── adapter.py
        ├── configuration.py
        └── persistence.py
```

Existing modules may remain as compatibility facades during migration. New modules must not import optional vendor packages at module import time unless the corresponding adapter is being instantiated.

This layout is a responsibility map, not permission to create empty abstraction files. A module is
introduced only when its responsibility exists. Conversely, discovery, loading, lifecycle, policy,
and runtime catalog behavior must not accumulate in a single registry module.

## Modularity and size guardrails

The current repository contains several concentration risks: `rag/pipeline.py` is approximately 729
lines, `cli/main.py` approximately 522 lines, and `ingestion/pipeline.py` approximately 374 lines.
Milestone one must not add vector or source responsibilities to these files.

The following guardrails apply:

- New production modules target 250 lines or fewer and require explicit review above 300 lines.
- New production modules above 350 lines fail the repository architecture check unless generated or
  covered by a short architecture decision record explaining why splitting would reduce cohesion.
- Existing files already above the threshold are recorded in a baseline and may not increase in
  non-comment source lines.
- Functions target 40 logical lines or fewer and cyclomatic complexity of 10 or less. Exceptions
  require a focused explanatory comment or refactoring note.
- Classes own one lifecycle and target 200 lines or fewer.
- Test modules are organized by behavior and target 350 lines or fewer; shared fixtures belong in
  narrowly scoped fixture modules rather than a growing global `conftest.py`.
- `__init__.py` files expose public names but contain no discovery, registration, or business logic.

These thresholds are maintainability tripwires rather than incentives to split cohesive logic into
arbitrary fragments. CI reports both line count and complexity, while review determines whether a
module still has one clear reason to change.

Because milestone one must modify ingestion and RAG vector access, it also extracts the affected
responsibilities instead of growing the existing pipeline modules:

```text
src/docpipe/ingestion/
├── pipeline.py              # backward-compatible facade only
├── coordinator.py           # use-case sequencing
├── document_builder.py      # parsed/extracted content normalization
├── incremental.py           # fingerprints and duplicate decisions
└── contextualization.py     # optional contextual chunk enrichment

src/docpipe/rag/
├── pipeline.py              # backward-compatible facade only
├── coordinator.py           # query use-case sequencing
├── generation.py            # prompt and answer generation
└── retrieval/
    ├── base.py              # strategy protocol and shared models
    ├── registry.py          # strategy selection, not execution
    ├── naive.py
    ├── hyde.py
    ├── multi_query.py
    ├── parent_document.py
    ├── hybrid.py
    ├── lightrag.py
    └── automatic.py
```

Unrelated CLI decomposition is not part of this milestone, but `cli/main.py` may not grow. Later CLI
work should split commands by domain.

## Dependency direction

The implementation follows ports-and-adapters boundaries without introducing a framework solely to
name the pattern:

```text
HTTP / CLI / SDK facades
          ↓
application coordinators
          ↓
Docpipe contracts and domain models
          ↑
vendor adapters and plugin factories
```

Domain models and contracts import only the Python standard library and existing core validation
primitives. Coordinators depend on narrow contracts supplied in their constructors. Vendor adapters
depend inward on contracts; contracts never import adapters. HTTP schemas map to application commands
at the interface boundary and do not become internal domain models merely for convenience.

An automated import-boundary test enforces these rules. At minimum it rejects vendor SDK imports in
contracts and coordinators, imports from server or CLI modules into application code, and imports from
concrete adapters into core pipelines. New cross-layer exceptions require an architecture decision
record, not an inline ignore.

Construction occurs in explicit composition roots for the SDK, CLI, and server. Constructors do not
read environment variables or call global settings functions. Configuration is parsed once, mapped to
typed settings, and injected. This makes runtime behavior reproducible and unit tests independent of
process state.

## Core data types

### Plugin descriptor

`PluginDescriptor` is immutable metadata suitable for API responses and discovery UI. It includes:

- Stable plugin name.
- Plugin category.
- Human-readable description.
- Implementation version when available.
- Installation extra or external package name.
- Availability and missing dependency information.
- Declared capabilities.
- License identifier and optional license note.
- Runtime requirements such as CPU, GPU, external service, or local binary.
- Deprecation state.
- Supported Docpipe plugin API version range.

Descriptors contain no secrets or live client instances. Descriptor construction must not establish network connections or load models.

### Plugin configuration

New transport configuration uses a typed envelope:

```python
PluginConfig(
    provider="qdrant",
    options={"url": "http://qdrant:6333", "collection": "documents"},
)
```

`options` is limited to a recursive `JSONValue` type at transport boundaries; `Any` is prohibited.
Immediately after plugin selection, the plugin factory validates this envelope into its immutable,
typed Pydantic configuration model. Untyped mappings do not enter coordinators or adapters. Unknown
options are rejected with a path-specific error. Secrets use `SecretStr` or an equivalent
Docpipe-owned secret type and are marked for central redaction.

Configuration may contain secret references, not embedded secret values, when it is serialized or
persisted. A `CredentialResolver` supplied by the composition root resolves environment, file,
workload-identity, or future secret-manager references immediately before adapter construction.
Resolved credentials remain scoped to the adapter instance and cannot be returned by model dumps.

Legacy `vector_backend`, `connection_string`, `table_name`, and related fields remain accepted. A compatibility mapper translates them to the new envelope before plugin resolution. Translation is isolated from adapter implementation.

### Capability declaration

Capabilities are stable string-valued enums rather than arbitrary booleans. Initial vector capabilities are:

- Dense search.
- Metadata filtering.
- Hybrid dense/sparse search.
- Delete by normalized source ID.
- Source aggregation.
- Collection creation.
- Collection health check.
- Transactional write, when genuinely supported.

Initial source capabilities are:

- Seekable artifact.
- Streaming access.
- Range requests.
- Content-length discovery.
- Content-type discovery.
- Source version identifier.

Calling services check declared capabilities before invoking optional operations. Unsupported operations raise `PluginCapabilityError` with the plugin and capability names. Capability names are versioned as part of the plugin API and are never inferred by `hasattr` checks.

### Operation context

Every plugin operation receives an immutable `OperationContext` containing request ID, trace context,
tenant identity, deadline, and idempotency key where applicable. It contains no provider credentials.
This prevents signatures from expanding whenever a cross-cutting concern is introduced and gives
adapters a consistent cancellation and observability boundary.

## Vector-store contract

The vector-store boundary follows interface segregation. A plugin factory returns only the facets
declared by its descriptor:

- `VectorWriter`: batch upsert and delete operations.
- `VectorReader`: dense search and optional hybrid search.
- `VectorCollectionAdmin`: create, validate, describe, and source aggregation.
- `PluginHealthProbe`: dependency health.

Core use cases request the narrow facet they require. Read-only integrations do not implement writer
methods, and embedded backends do not implement meaningless remote-service operations.

Contracts use structural `Protocol` types so third-party plugins do not need to inherit Docpipe base
classes. A typed `VectorStoreBinding` groups optional reader, writer, administration, and health
facets for lifecycle management; it contains no business behavior. Factory validation ensures the
binding and descriptor advertise exactly the same capabilities.

Input and output types are Docpipe-owned immutable models. They include vector values, content, normalized metadata, scores, source identifiers, collection identifiers, pagination, and partial-write outcomes where applicable. Vendor result objects and LangChain `Document` objects never cross the adapter boundary.

Embedding generation is separate from vector persistence. The vector writer receives already embedded
`VectorRecord` values, and the vector reader receives a `VectorQuery` containing an already embedded
dense vector plus optional sparse vector and safe filter expression. A small internal
`EmbeddingEncoder` port isolates the existing LangChain embedding objects during milestone one; a
public provider plugin category can replace it later. This separation prevents every vector backend
from depending on LangChain and enables generic OpenAI-compatible, LiteLLM, and local encoders later.

Service-facing contracts are asynchronous. Blocking vendor SDKs run through a centrally configured
blocking runner with bounded concurrency rather than calling `asyncio.to_thread` independently.
Synchronous SDK entry points use an explicit sync facade; they do not invoke nested event loops.
Descriptors declare whether instances are safe to share and whether they require operation-, request-,
or process-scoped lifetime.

`PluginRuntime` owns instantiated resources through `AsyncExitStack` and closes them deterministically
at request or application shutdown. Plugins with no owned resources do not need an artificial close
method; lifecycle is supplied only by factories that create managed resources.

Upserts use deterministic record IDs and accept an idempotency key. `WriteBatchResult` reports
accepted, rejected, and uncertain records so partial failures cannot be mistaken for success.
Descriptors declare consistency and atomicity semantics. Conformance tests verify that retrying the
same logical write does not create duplicates when the backend advertises idempotent upsert behavior.
Batch size and in-flight concurrency are centrally bounded to provide backpressure.

## Source resolver contract

`SourceResolver` converts an external source URI into a normalized `ResolvedSourceHandle`:

- Canonical source ID safe for metadata and incremental ingestion.
- Display name.
- A lifecycle-bound content handle that can stream or materialize to a local path.
- Content type and length when known.
- Version identifier, checksum, or modification marker when known.
- Safe metadata.
- Explicit cleanup ownership.

The resolver contract covers:

1. URI support detection without external I/O.
2. Configuration validation.
3. Safe resolution with timeout and size limits.
4. Resource cleanup through an asynchronous context manager.

Local resolution rejects disallowed paths and preserves the existing source-safety policy. HTTP resolution retains SSRF protections, redirect limits, timeouts, and response-size enforcement. Temporary files use restricted permissions and are removed by the resolver that created them.

The handle exposes `open()` and `materialize()` operations rather than a path-or-stream union. Parsers
that require a filesystem path call `materialize()`; streaming parsers call `open()`. Both remain
inside the same asynchronous context manager, preventing ambiguous cleanup ownership.

Parser code receives the resolved handle rather than downloading arbitrary URLs itself. Original source identity remains available for result metadata and incremental-ingestion decisions. Content fingerprints are computed from resolved bytes or trusted provider version metadata, never from the URI string alone.

Existing parser plugins continue receiving the path or URI form they support through a
`ParserInputAdapter`. Path-only parsers receive a materialized path, streaming-aware parsers may opt
into the handle contract, and unchanged third-party parsers remain compatible. Source resolution and
temporary-resource ownership stay outside parser implementations.

Provider ETags and version IDs are treated as version tokens, not automatically as cryptographic
content hashes. The default incremental-ingestion identity is a digest of resolved content. Operators
may explicitly choose a trusted provider version token to avoid downloading unchanged objects.
Failure to query incremental state is an error by default; it must not silently fail open and create
duplicates. An explicit best-effort policy may retain legacy behavior during migration.

## Discovery and lifecycle

Python entry-point groups are:

```toml
[project.entry-points."docpipe.vectorstores"]
pgvector = "docpipe.vectorstores.pgvector:PgVectorBackend"
turbovec = "docpipe.vectorstores.turbovec:TurboVecBackend"

[project.entry-points."docpipe.sources"]
file = "docpipe.sources.local:LocalSourceResolver"
http = "docpipe.sources.http:HttpSourceResolver"
```

Discovery has three phases:

1. Enumerate installed entry-point and distribution metadata without importing plugin code.
2. Resolve policy, duplicate names, and plugin API compatibility.
3. Load and instantiate the selected implementation on demand.

Python entry points expose a name and import target but cannot provide a rich descriptor without
executing plugin code. Therefore, third-party distributions may ship a versioned
`docpipe-plugin.json` manifest in distribution metadata. Discovery validates this static manifest
against a Docpipe JSON Schema. A plugin without a manifest is shown with basic distribution metadata
and obtains its full descriptor only when explicitly loaded. Official built-ins use checked-in static
descriptors. Malformed manifests mark that plugin unavailable without affecting other registrations.

Discovery failures are isolated per plugin. One broken optional plugin must not prevent Docpipe startup or hide other plugins. Failures are logged once with the plugin name and safe error category. `/plugins` reports unavailable integrations and actionable installation guidance.

Entry-point names are unique within a category. Duplicate third-party registrations fail selection
deterministically rather than depending on installation order. Official built-ins are not silently
overridden. Operators may configure per-category allowlists and denylists.

Installed plugins execute trusted Python code in the Docpipe process. Discovery metadata is not a
sandbox or security boundary. Documentation must state this explicitly, and production deployments
should use allowlists when the environment contains packages outside operator control.

Each plugin declares a plugin API version range. Incompatible plugins remain visible as unavailable
with a clear compatibility error; they are not imported. Contract evolution follows semantic
versioning, with additive optional capabilities preferred over changes to existing facet signatures.

The new runtime consists of three distinct objects:

- `PluginCatalog`: immutable registrations and descriptors after application startup.
- `PluginLoader`: lazy import, compatibility validation, and typed factory construction.
- `PluginRuntime`: scoped instances and deterministic resource cleanup.

These objects are created in the SDK/server composition root and injected into coordinators. The
current process-global `PluginRegistry` remains only as a compatibility facade during milestone one.
New core code must not call `PluginRegistry.get()`. Tests construct isolated catalogs without global
reset operations, enabling parallel execution.

## Error model

Public plugin exceptions are stable and independent of vendor SDKs:

```text
PluginError
├── PluginNotFoundError
├── PluginDependencyError
├── PluginConfigurationError
├── PluginCapabilityError
└── PluginOperationError

SourceError
├── UnsupportedSourceError
├── SourceAccessError
├── SourceTooLargeError
└── UnsafeSourceError

VectorStoreError
├── VectorStoreConnectionError
├── CollectionNotFoundError
└── VectorStoreOperationError
```

Adapters translate vendor errors at their boundary and preserve the original exception with `raise ... from exc`. Exceptions carry a stable error code, safe context, retry classification, and optional operator hint. They never contain credentials or raw vendor configuration.

Retry classification is an enum (`never`, `transient`, `throttled`, `unknown`) with optional safe
retry-after metadata. Adapters do not sleep or retry unless a vendor client performs a documented,
bounded transport retry. Future orchestrators consume the classification and own workflow policy.

HTTP mapping uses stable status codes and response error codes. Authentication and authorization failures remain distinguishable from upstream availability failures without revealing credential details.

## Logging and observability

Plugin operations emit structured events with stable names:

```text
plugin.discovery.started
plugin.discovery.completed
plugin.load.failed
source.resolve.started
source.resolve.completed
source.resolve.failed
vectorstore.upsert.started
vectorstore.upsert.completed
vectorstore.upsert.failed
vectorstore.search.started
vectorstore.search.completed
vectorstore.search.failed
```

Safe common fields include:

- Plugin name and category.
- Operation.
- Request and trace IDs.
- Tenant identifier when available.
- Duration.
- Record or result count.
- Outcome and stable error code.
- Retry classification.

Connection strings, API keys, signed URLs, authorization headers, document content, embedding vectors, and unrestricted metadata are prohibited. Redaction applies recursively to mappings and URLs before fields reach a logger. Logging failures must not fail the business operation.

Existing OpenTelemetry spans wrap the same operation boundaries and use the same safe attribute vocabulary. Metrics use bounded-cardinality labels only; collection, source URI, tenant, and exception message are not metric labels.

Tenant identifiers in logs follow the deployment privacy policy and may be replaced with a stable
opaque identifier. Raw user-supplied identifiers are never assumed safe merely because they are not
credentials.

## Documentation and code comments

Every public contract, model, exception, and adapter method requires a docstring covering:

- Purpose and observable behavior.
- Arguments and return value.
- Raised public exceptions.
- Side effects and owned resources.
- Concurrency and async-safety expectations.
- Credential and data-handling expectations where relevant.

Comments document invariants and non-obvious constraints, such as idempotency, cleanup ownership, vendor limitations, or security decisions. Comments must not narrate straightforward statements.

Documentation deliverables include:

- Architecture overview.
- Plugin-author guide.
- Vector-store and source contract reference.
- Configuration and secret-handling guide.
- Migration guide for legacy configuration.
- Operator troubleshooting guide.
- Minimal third-party plugin example outside the core package namespace.

Examples must use placeholders that cannot be mistaken for real credentials. Executable snippets are tested where practical.

## Testing strategy

### Contract tests

Reusable suites define observable behavior for vector stores and source resolvers. Official and third-party plugin authors can import these suites. Tests cover happy paths, invalid configuration, missing dependencies, unsupported capabilities, cleanup, idempotency, metadata normalization, exception translation, and redaction.

The public test kit ships under `docpipe.testing`, with versioned fixtures and no dependency on the
repository's internal `tests/` package. Each suite records which plugin API version it certifies.

### Unit tests

Unit tests cover descriptor construction, lazy discovery, duplicate registration, configuration validation, compatibility mapping, capability negotiation, safe error serialization, and recursive redaction. Vendor boundaries are mocked; internal behavior is not mocked merely to satisfy implementation details.

### Integration tests

Real-service tests cover pgvector and TurboVec in milestone one. They validate collection lifecycle, ingestion, search, filtering, deletion, source aggregation, health checks, cleanup, and concurrent use. Integration tests are isolated with unique collection names and deterministic cleanup.

### Compatibility tests

Existing SDK calls, CLI commands, and HTTP requests must retain their response shapes and semantics. Golden tests compare old configuration paths with equivalent namespaced configurations.

### Security and failure tests

Tests cover path traversal, HTTP SSRF, redirect abuse, oversized sources, timeouts, invalid credentials, partial vendor failures, unavailable services, malformed metadata, cleanup after cancellation, and credential redaction in logs and HTTP errors.

Vector-store security tests also cover safe collection-name handling and filter compilation. Core
filters use a typed Docpipe expression tree; adapters compile that tree through vendor APIs or
parameterized queries. Raw SQL and vendor query fragments are not accepted through public requests.

### Static quality gates

- Ruff formatting and linting.
- Strict mypy for new contracts, models, and adapters.
- Documentation build and link validation.
- `git diff --check`.
- Dependency audit for newly introduced optional packages.
- Architecture check for module growth, dependency direction, and forbidden vendor imports.

## Continuous integration

CI is divided by cost:

1. Core unit, contract, compatibility, lint, and type tests on every pull request.
2. One affected-adapter job per optional plugin.
3. Service-container integration tests for pgvector and later Qdrant/MinIO.
4. Scheduled compatibility runs across supported dependency ranges.
5. Scheduled full integration runs for expensive combinations.

Tests must not require production credentials. Live cloud integration tests, if introduced later, run only in explicitly protected workflows.

## Migration sequence

1. Add plugin-owned models, descriptors, configuration, errors, and redaction utilities.
2. Add plugin API versioning, trust policy, category-neutral catalog, lazy loader, and scoped runtime.
3. Define Docpipe-owned vector records, queries, filter expressions, write outcomes, and the internal embedding encoder port.
4. Define segregated vector facets and their conformance suites.
5. Extract vector-related sequencing from the existing ingestion and RAG monoliths into injected coordinators.
6. Adapt pgvector without changing public behavior.
7. Adapt TurboVec and run the identical conformance suites.
8. Replace vector backend conditionals in ingestion, search, deletion, source aggregation, and health logic.
9. Define source handles, resolver protocol, and conformance suite.
10. Move local-file safety and lifecycle behavior into `LocalSourceResolver`.
11. Move URL validation and download behavior into `HttpSourceResolver`.
12. Route parse and ingest source handling through resolution.
13. Add legacy-to-namespaced configuration translation and compatibility tests.
14. Extend `/plugins` and `/profiles` with safe capability and availability metadata.
15. Publish architecture decisions, plugin-author, migration, configuration, and troubleshooting documentation.
16. Complete the full quality gate before milestone two begins.

## Compatibility and deprecation

No existing public fields are removed in milestone one. Legacy and new configuration cannot silently conflict: when both specify the same concern with different values, Docpipe raises a path-specific configuration error. When values agree, namespaced configuration takes precedence without changing behavior.

Deprecation warnings are emitted once per process and point to the migration guide. They are not emitted per document or chunk. Removal requires a later major version and a documented support window.

Public contracts carry an explicit stability level: `experimental`, `stable`, or `deprecated`.
Milestone-one contracts remain experimental through the pgvector and TurboVec migration and become
stable only after Qdrant and S3/MinIO validate the extension boundary in milestone two. Stable
contract changes follow semantic versioning. Serialized command, result, descriptor, and error models
carry schema versions when persisted or sent across a durable job boundary.

Migration is guarded by one temporary runtime switch used in tests and staged deployments. Both paths
are not maintained indefinitely: after compatibility and integration gates pass, the new path becomes
the default, the old path remains available for one release as rollback protection, and then the
internal legacy path is removed independently of public field deprecation.

## Milestone-one acceptance criteria

Milestone one is complete when:

1. pgvector and TurboVec pass the same vector-store conformance suite.
2. Local and HTTP inputs pass the same source-resolver conformance suite.
3. Existing supported SDK, CLI, and HTTP behavior passes compatibility tests.
4. Core services contain no pgvector/TurboVec-specific execution branches.
5. Plugin discovery reports missing optional dependencies without failing startup.
6. Security tests prove credential and signed-URL redaction.
7. New public APIs pass strict type checking and have complete docstrings.
8. Structured logs and traces use documented safe fields.
9. Base installation dependencies do not increase.
10. Plugin-author, migration, configuration, and troubleshooting documentation is published.
11. New core code uses injected `PluginCatalog`, `PluginLoader`, and `PluginRuntime`; it does not read process-global registry state.
12. Vendor and LangChain types do not cross source, embedding, or vector-store boundaries.
13. No new module exceeds the architecture thresholds, and touched oversized modules do not grow.
14. Plugin API compatibility and duplicate-registration behavior are deterministic and tested.
15. Resource cleanup, partial writes, deadlines, bounded concurrency, and idempotent retries are tested.
16. Import time, memory, and representative ingest/search latency do not regress beyond an explicitly recorded baseline without an approved architecture decision.

## Milestone two preview

Milestone two validates extensibility by adding:

- `QdrantBackend` through the vector-store entry point and `qdrant` extra.
- `S3SourceResolver` supporting AWS S3 and S3-compatible systems such as MinIO through the source entry point and `s3` extra.
- Real Qdrant and MinIO integration-test jobs.
- Reference documentation showing external plugin packaging.

Qdrant and S3/MinIO must not require changes to core ingestion control flow. Any such required change indicates an incomplete milestone-one contract and must be resolved in the contract rather than through vendor-specific branching.
