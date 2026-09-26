# Authoring a Docpipe plugin

Start from [`examples/plugin-package`](../../examples/plugin-package/README.md). It is a complete external wheel, not an in-tree adapter. Its entry point and `docpipe-plugin.json` manifest let Docpipe discover capabilities and installation requirements without importing the implementation.

1. Pick a stable lowercase name and a `source` or `vectorstore` category.
2. Add a `docpipe.sources` or `docpipe.vectorstores` entry point. Export a factory accepting `PluginConfig` and keyword-only `PluginFactoryContext`.
3. Include a versioned manifest in the wheel's `.dist-info` directory. The published format is described by [`manifest.schema.json`](../../src/docpipe/plugins/manifest.schema.json); runtime validation uses strict Pydantic models, with parity covered by tests. Declare actual capabilities only, and keep descriptions free of secrets and local paths.
4. Validate `config.options` in the selected factory with a provider-owned typed model. Return safe `PluginConfigurationError` field paths such as `vector_store.options.url`.
5. Implement the relevant public facets and resource lifecycle. Do not import another adapter's private classes.
6. Run `assert_vector_store_conformance` or `assert_source_conformance` from `docpipe.testing` against an instance, then build and install the wheel in a clean environment.

The vector conformance helper checks create, upsert, search, delete-by-source, and health. The source helper checks support, streaming, digest, materialization, and cleanup. They test behavior, not a vendor SDK. Additional capability-specific tests are still required—for example filter compilation, timeouts, partial writes, and cancellation.

Plugin API `1.0.0` is currently experimental. Read the [compatibility policy](compatibility.md) before distributing a plugin; it defines stability gates, version negotiation, and the compatibility promise that applies after API v1 is stable. See [configuration](configuration.md), [security](security.md), and [troubleshooting](troubleshooting.md).
