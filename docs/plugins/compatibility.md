# Plugin API compatibility policy

## Current status

Plugin API `1.0.0` remains **experimental**. The vector-store and source contracts will be marked
stable only after pgvector, TurboVec, Qdrant, local files, HTTP, and S3-compatible sources pass their
shared conformance suites, including service-backed Qdrant and SeaweedFS checks. The S3 adapter
accepts MinIO-style endpoints, but this repository does not run its service-backed integration suite
against MinIO itself. Until the stable release is published, compatible additive changes are
preferred, but plugin authors should not assume a stable API or deploy an experimental plugin across
independently upgraded environments.

## Version negotiation

Every plugin descriptor declares an inclusive `api_min` and `api_max` range. Docpipe loads a plugin
only when its own `DOCPIPE_PLUGIN_API_VERSION` falls inside that range. An incompatible plugin stays
visible in discovery as unavailable and is not imported. Plugins must declare the actual range they
support; wildcard or guessed ranges are not accepted as a compatibility guarantee.

The plugin API version is separate from both the Docpipe package version and a plugin's own
implementation version. A plugin's distribution may release independently as long as it continues
to satisfy the declared contract.

## Changes after API 1.0 becomes stable

Stable contracts follow semantic versioning:

- **Patch:** fixes that preserve documented inputs, outputs, capability semantics, and lifecycle
  behavior; security fixes; and documentation corrections.
- **Minor:** backward-compatible additions, such as a new optional field, capability, or extension
  point. New enum values are documented as potentially unknown to older consumers; callers must
  handle unknown optional capabilities safely.
- **Major:** removals or renames, newly required fields, changed meaning of existing fields or
  capabilities, incompatible lifecycle changes, or behavior that invalidates a documented contract.

Changing a default is considered breaking when it changes observable behavior for a consumer that
did not opt in. It requires a major version unless the old behavior was explicitly documented as
unstable or unsafe and a security advisory explains the exception.

## Deprecation and migration

Deprecations are announced in release notes and the relevant migration documentation. A deprecated
public contract remains available for the rest of its current major version; removal requires a new
major version. When a security issue requires earlier removal, Docpipe publishes a security notice,
the affected surface, and a migration path. Deprecation warnings are emitted at a public boundary and
must not be repeated per document or chunk.

Legacy SDK, CLI, and HTTP configuration remains supported according to the compatibility guarantees
documented by that interface. Plugin API compatibility does not itself authorize removing those
separate public interfaces.

## What the stability guarantee covers

The guarantee covers the documented exports from `docpipe.plugins`, vector-store and source
contracts, their immutable domain models, stable plugin errors, factory context, and the public
conformance helpers in `docpipe.testing`. Internal modules, vendor-specific configuration classes,
provider SDK objects, and unexported helpers are implementation details unless a later document
explicitly promotes them.

A stable release requires the shared conformance suite for every reference adapter, the external
example-plugin wheel test, compatibility tests, strict typing and architecture gates, and the
service-backed integration jobs for Qdrant and the configured S3-compatible CI service. If a
required service-backed check has not run successfully for a release candidate, the corresponding
contract remains experimental; a skipped local test is not treated as a pass. MinIO-specific
interoperability must be tested against a supported MinIO deployment before claiming that evidence.
