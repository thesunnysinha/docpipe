# Plugin architecture

Docpipe selects plugins by stable names, never by a class name supplied in a request. Static distribution metadata builds an immutable catalog without importing implementation modules. A policy-gated loader imports only the selected implementation, validates its API version, and constructs it with explicitly owned runtime services.

The first extension categories are `vectorstore` and `source`. Vector stores expose independent reader, writer, collection-admin, and health facets. Source resolvers expose managed handles with streaming and materialization. Core coordinators consume only immutable domain models and protocols; vendor SDK objects remain inside adapters.

The selection sequence is: catalog registration → process and tenant policy → API compatibility → lazy factory import → provider-specific option validation → operation/request resource scope → facet negotiation. Discovery is side-effect-free. A missing or prohibited plugin stays visible in `/plugins` but cannot be loaded.

Plugin instances that own resources should implement context-manager entry and exit. Request and operation scopes close resources on success, failure, and cancellation. The server's shallow `/health` does not import optional plugins; `/plugins/health` probes only the configured vector provider with a deadline.

The model layout follows the workflow boundary: public domain models live in `docpipe.core.schemas.documents`, `.extraction`, `.ingestion`, `.rag`, and `.evaluation`; `docpipe.core.types` re-exports them for existing SDK callers. HTTP request/response schemas remain in `docpipe.schemas`. Provider-only validated settings live beside their adapters in `docpipe.sources.s3.schemas` and `docpipe.vectorstores.qdrant.schemas`; their old `configuration` imports remain aliases. Domain exceptions live in `docpipe.core.errors`, `docpipe.plugins.errors`, and `docpipe.ingestion.errors`, with old import paths retained as aliases where necessary.

`DOCPIPE_PLUGIN_FOUNDATION_ENABLED=false` temporarily restores only the legacy pgvector/TurboVec ingestion facade for staged rollback. Source resolution always remains policy-gated; raw request sources are never passed directly to parsers. The switch defaults to true and should be removed after one compatibility release.

Plugin API `1.0.0` contracts remain experimental until the reference Qdrant and S3/MinIO adapters pass the shared conformance suites. See the [compatibility policy](../plugins/compatibility.md), [authoring guide](../plugins/authoring.md), and [dependency boundaries](dependency-boundaries.md).

The current local adapter comparison is recorded in the [plugin performance baseline](../plugins/performance.md); it is not a substitute for the service-backed release measurements.

The flat operator settings schema remains a compatibility surface. Its size review and decomposition criteria are recorded in [ADR 0002](decisions/0002-flat-settings-schema.md).
