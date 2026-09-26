# Plugin foundation performance baseline

This is a local adapter microbenchmark, not a production capacity claim. It provides a repeatable
comparison between the plugin path and its temporary legacy rollback path. The reproducible harness
is [`scripts/benchmark_plugin_foundation.py`](../../scripts/benchmark_plugin_foundation.py).

## Workload and environment

Measured on 2026-09-26 with Python 3.13.13, macOS 26.6.2, arm64, and 10 available CPUs. TurboVec
1.0.0 provided the local on-disk vector index. Each of three trials per path ran in a fresh process
with a fresh temporary collection, ingested 32 records, then issued 20 searches. Both paths used
the same deterministic eight-dimensional test embedder and an identity chunker; no network service,
provider API, or real embedding model was involved. Peak RSS includes interpreter and runtime startup.

The plugin path used `DOCPIPE_PLUGIN_FOUNDATION_ENABLED=true`; the baseline used the supported
rollback setting `false`. Ingestion time includes first-collection creation and is reported per
record. Search percentiles pool the 60 queries per path. The plugin search sample includes its
operation-scoped reader acquisition; the rollback sample uses the legacy vector-store facade.

| Path | Ingest median / record | Search p50 | Search p95 | Median peak RSS |
| --- | ---: | ---: | ---: | ---: |
| Legacy rollback | 16.09 ms | 0.290 ms | 0.473 ms | 84.66 MiB |
| Plugin | 14.35 ms | 0.462 ms | 0.830 ms | 65.00 MiB |

On this small local workload, plugin ingestion was about 11% faster and peak RSS about 23% lower;
search p50 was about 0.17 ms slower. These results are directional only: one local index, 32 records,
no concurrent load, and no server-side network/storage costs. Do not use them to size deployments or
claim Qdrant/pgvector/MinIO performance.

The default harness settings reproduce the workload:

```bash
python scripts/benchmark_plugin_foundation.py
```

Use `--records`, `--queries`, and `--trials` to scale the local run. The `turbovec` extra must be
installed. On platforms without the standard-library `resource` module, latency results remain
available and peak RSS is reported as unavailable.

## Import cost comparison

As a separate check, 20 fresh Python processes per source tree measured `import docpipe` using the
same Python 3.13.13 environment. The pre-plugin baseline was commit `7fb10a3`; the plugin result was
commit `b2c3f39` plus its in-progress worktree changes.

| Source tree | Import median | Import p95 | Median peak RSS |
| --- | ---: | ---: | ---: |
| Pre-plugin baseline | 113.33 ms | 115.56 ms | 40.13 MiB |
| Plugin foundation | 114.29 ms | 116.45 ms | 44.10 MiB |

The measured import-time change was under 1 ms in the median; peak import RSS increased by about
4 MiB. This is a process-startup measurement, not steady-state server memory. Re-run it after the
worktree changes are committed and on supported Python versions before treating it as a release
baseline.

## Remaining release evidence

The local results do not replace live-service measurements. Before plugin API `1.0.0` can be marked
stable, run the documented CI integration profiles against pgvector, remote Qdrant, and MinIO/S3,
then add those workload sizes, deployment resources, latency percentiles, and RSS measurements here.
The current local environment has no PostgreSQL DSN or MinIO endpoint; Docker image listing fails
because the host's containerd content store reports an I/O error. API v1 therefore remains
experimental.
