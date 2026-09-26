# Test layout

Tests are grouped first by scope (`unit`, `integration`, `compat`, `architecture`, `packaging`, and `docs`), then by the component or public behavior they exercise. New behavior modules use descriptive `*_spec.py` filenames and `should_*` case names; pytest is configured to discover these alongside the existing `test_*` convention. The older names remain supported so migration does not obscure coverage or break downstream test commands.

Keep a behavior spec focused on one concern, normally below 200 lines. Put reusable fake clients, distribution metadata, and transport helpers in `support.py` or a narrowly scoped `conftest.py`, not among assertions in a large endpoint file. Fixtures should construct fresh state for each case. Integration specs must skip only when their external service is intentionally unavailable locally; their dedicated CI jobs provide the required live-service run.

For plugin adapters, use the published conformance helpers from `docpipe.testing` and add focused cases for provider-specific policy, deadlines, failures, lifecycle cleanup, and safe diagnostics. Do not duplicate a vendor SDK inside the test double when a SDK stub or local mode can exercise the real request shape.
