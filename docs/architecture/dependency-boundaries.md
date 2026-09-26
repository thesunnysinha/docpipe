# Dependency boundaries

`docpipe.plugins.contracts` and `docpipe.testing` are public, vendor-neutral packages. They may depend on the Python standard library and Docpipe domain models, but not on Qdrant, boto3, psycopg, TurboVec, LangChain vector stores, FastAPI, or a process-global registry.

Application composition translates legacy SDK types at the edge. Ingestion and RAG coordinators receive encoders, readers, writers, and lifecycle owners through constructors. Concrete adapters depend inward on the contracts, never the reverse. HTTP schemas and configuration envelopes hold JSON-safe data; provider factories perform typed validation after selection and policy checks.

Optional integration SDKs belong only in extras. The base package must import and discover metadata when no optional integration is installed. A selected missing integration raises an actionable dependency error. New adapters must not add provider-specific branches to ingestion, RAG, parser, or router control flow.

Structured events contain provider name, category, counts, durations, and safe error codes. They do not contain content, vectors, prompts, source URLs, DSNs, credentials, or provider exception messages.
