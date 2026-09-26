# ADR 0001: Enforce plugin dependency boundaries

## Status

Accepted.

## Context

Docpipe is expanding from five plugin categories to independently installable source and vector-store integrations. Existing ingestion and RAG pipelines directly construct concrete backends and read global settings, which makes additional integrations progressively harder to test and maintain. Several existing modules are already large enough that adding more branching would make them monolithic.

## Decision

Docpipe will use ports-and-adapters dependency direction:

- Contracts and domain models do not import vendor libraries.
- Coordinators depend on injected, capability-specific protocols.
- Concrete adapters depend inward on Docpipe contracts.
- SDK, CLI, and server composition roots construct runtime dependencies.
- New modules target 250 logical lines and fail above 350 unless an ADR justifies an exception.
- Existing oversized modules are baselined and cannot grow.

Architecture checks run in CI. Exceptions require a new ADR rather than an inline suppression.

## Consequences

Plugin implementations remain independently installable and testable. Existing large modules must be reduced as their responsibilities are migrated. The project accepts modest up-front structure to prevent vendor-specific branches, global state, and resource-lifecycle behavior from accumulating in central files.
