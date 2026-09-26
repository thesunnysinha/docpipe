# ADR 0002: Keep flat operator settings in one schema

## Status

Accepted.

## Context

`DocpipeSettings` contains settings for the SDK and server across plugin selection, ingestion,
observability, source security, transcription, and the optional control plane. Per-field schema
descriptions increased this module to 317 logical lines, crossing the architecture review threshold.
The module declares configuration and three small resolution helpers; it does not own runtime or
provider behavior.

## Decision

Keep one flat `BaseSettings` model as the public operator configuration surface. Existing
environment variable names such as `DOCPIPE_CHUNK_SIZE` and flat YAML keys are compatibility
contracts. Splitting configuration into nested settings models would change environment variable
names or require duplicate aliases and mapping code across every supported field. The current
module-size warning is therefore an explicit, reviewed exception, not a general exemption from the
size gate.

Continue to keep provider-specific settings beside each adapter. Split the application settings
schema only if executable behavior accumulates here, the module exceeds the 350-line hard limit, or
flat aliases can be preserved with a tested composition that is simpler than the current schema.

## Consequences

Operators keep a single source of truth with stable flat keys, and generated schema descriptions
remain attached to each setting. Architecture CI continues to report the review warning; future
growth in this module requires a separate ADR or decomposition rather than increasing the limit.
