"""Compare the plugin ingestion path with the legacy rollback path locally."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.core.types import DocumentFormat, IngestionConfig, ParsedDocument
from docpipe.ingestion.pipeline import IngestionPipeline
from docpipe.ingestion.search_composition import build_search_coordinator


class DeterministicEmbeddings:
    """Provide stable, network-free vectors for adapter comparisons."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one eight-dimensional vector per input document."""
        return [[float(len(text) % 7)] * 8 for text in texts]

    def embed_query(self, text: str) -> list[float]:
        """Return a deterministic query vector."""
        return [float(len(text) % 7)] * 8


class IdentityChunker:
    """Keep each generated document as one vector record."""

    def split_documents(self, documents: list[object]) -> list[object]:
        """Return documents unchanged so chunking cost is excluded."""
        return documents


@dataclass(frozen=True, slots=True)
class TrialResult:
    """Measurements from one fresh process and one temporary collection."""

    ingestion_ms_per_record: float
    search_latencies_ms: tuple[float, ...]
    peak_rss_mib: float | None


async def _measure_trial(
    *,
    plugin_enabled: bool,
    records: int,
    queries: int,
) -> TrialResult:
    """Measure one local TurboVec run without external model or service calls."""
    with tempfile.TemporaryDirectory(prefix="docpipe-foundation-benchmark-") as index_root:
        settings = DocpipeSettings(
            plugin_foundation_enabled=plugin_enabled,
            turbovec_index_dir=index_root,
        )
        runtime = build_runtime(settings)
        config = IngestionConfig(
            connection_string="unused-local-index",
            table_name="benchmark_documents",
            embedding_provider="deterministic-test",
            embedding_model="eight-dimensional-test",
            vector_backend="turbovec",
            turbovec_index_dir=index_root,
            ingest_mode="chunks",
        )

        original_embeddings = IngestionPipeline._create_embeddings
        original_chunker = IngestionPipeline._create_chunker
        IngestionPipeline._create_embeddings = staticmethod(lambda _: DeterministicEmbeddings())
        IngestionPipeline._create_chunker = staticmethod(lambda _: IdentityChunker())
        try:
            async with runtime:
                pipeline = IngestionPipeline(config, runtime=runtime)
                started = time.perf_counter()
                for index in range(records):
                    parsed = ParsedDocument(
                        source=f"benchmark-document-{index}.txt",
                        format=DocumentFormat.TEXT,
                        text=f"document {index} " * 64,
                    )
                    await pipeline.aingest(parsed)
                ingestion_ms_per_record = (time.perf_counter() - started) * 1000 / records

                search_latencies: list[float] = []
                for _ in range(queries):
                    search_started = time.perf_counter()
                    if plugin_enabled:
                        async with runtime.plugin_runtime.request_scope() as scope:
                            coordinator = await build_search_coordinator(
                                config,
                                runtime=runtime,
                                scope=scope,
                                embeddings=DeterministicEmbeddings(),
                            )
                            await coordinator.search("document query", limit=8)
                    else:
                        pipeline.search("document query", top_k=8)
                    search_latencies.append((time.perf_counter() - search_started) * 1000)
        finally:
            IngestionPipeline._create_embeddings = original_embeddings
            IngestionPipeline._create_chunker = original_chunker

    return TrialResult(
        ingestion_ms_per_record=ingestion_ms_per_record,
        search_latencies_ms=tuple(search_latencies),
        peak_rss_mib=_peak_rss_mib(),
    )


def _peak_rss_mib() -> float | None:
    """Return process peak resident memory where the platform exposes it."""
    try:
        import resource
    except ImportError:  # pragma: no cover - resource is not available on Windows.
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return peak / (1024 * 1024)
    return peak / 1024


def _percentile(values: Sequence[float], percentile: float) -> float:
    """Return a nearest-rank percentile from a non-empty sample."""
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]


def _summarize(label: str, trials: list[TrialResult]) -> dict[str, object]:
    """Calculate robust central and tail latency summaries for a path."""
    search_latencies = [latency for trial in trials for latency in trial.search_latencies_ms]
    rss_values = [trial.peak_rss_mib for trial in trials if trial.peak_rss_mib is not None]
    return {
        "path": label,
        "trials": len(trials),
        "ingestion_median_ms_per_record": statistics.median(
            trial.ingestion_ms_per_record for trial in trials
        ),
        "search_p50_ms": statistics.median(search_latencies),
        "search_p95_ms": _percentile(search_latencies, 0.95),
        "peak_rss_median_mib": statistics.median(rss_values) if rss_values else None,
    }


def _run_child(mode: str, *, records: int, queries: int) -> TrialResult:
    """Run one isolated trial so peak RSS does not accumulate across paths."""
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            mode,
            "--records",
            str(records),
            "--queries",
            str(queries),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    return TrialResult(
        ingestion_ms_per_record=payload["ingestion_ms_per_record"],
        search_latencies_ms=tuple(payload["search_latencies_ms"]),
        peak_rss_mib=payload["peak_rss_mib"],
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse repeatable workload controls for the benchmark command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=32, help="records ingested per trial")
    parser.add_argument("--queries", type=int, default=20, help="queries per trial")
    parser.add_argument("--trials", type=int, default=3, help="fresh-process trials per path")
    parser.add_argument(
        "--worker",
        choices=("legacy", "plugin"),
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    if args.records < 1 or args.queries < 1 or args.trials < 1:
        parser.error("records, queries, and trials must all be positive")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    """Run both paths and print machine-readable local measurements."""
    args = _parse_args(argv)
    if args.worker:
        result = asyncio.run(
            _measure_trial(
                plugin_enabled=args.worker == "plugin",
                records=args.records,
                queries=args.queries,
            )
        )
        print(json.dumps(asdict(result)))
        return 0

    summaries = []
    for mode, label in (("legacy", "legacy rollback"), ("plugin", "plugin")):
        trials = [
            _run_child(mode, records=args.records, queries=args.queries) for _ in range(args.trials)
        ]
        summaries.append(_summarize(label, trials))
    print(json.dumps({"environment": sys.platform, "results": summaries}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
