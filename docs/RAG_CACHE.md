# RAG response cache

HTTP RAG caching is opt-in. It caches exact-question responses in an async KV
backend, so a cache hit avoids retrieval, embedding, and generation work. The
standalone `RAGPipeline` SDK keeps its existing instance-local semantic cache
behavior; the server injects its app-owned backend into each request pipeline.

## Configuration

Caching is disabled unless explicitly enabled:

```dotenv
DOCPIPE_RAG_CACHE_ENABLED=true
DOCPIPE_RAG_CACHE_BACKEND=redis
DOCPIPE_RAG_CACHE_REDIS_URL=rediss://cache-user:secret@redis.example:6379/0
DOCPIPE_RAG_CACHE_TTL_SECONDS=300
DOCPIPE_RAG_CACHE_MAX_PAYLOAD_BYTES=262144
DOCPIPE_RAG_CACHE_SOCKET_TIMEOUT_SECONDS=1.0
```

Install the optional client with `pip install 'docpipe-sdk[rag-redis]'`. Redis
must be managed by the operator. Use a private network, TLS (`rediss://`), ACLs,
and a dedicated database or key prefix. The cache does not configure Redis
eviction policy, persistence, replication, or high availability.

`DOCPIPE_RAG_CACHE_BACKEND=memory` uses a process-local LRU cache bounded by
`DOCPIPE_RAG_CACHE_MAX_ENTRIES`; it is suitable for development or a single
worker only. It is not shared across workers/replicas and is cleared at server
shutdown. Redis shares entries across processes that use the same Redis
deployment, but its durability and availability depend entirely on the
operator's Redis configuration.

## Isolation and failure behavior

The server uses a SHA-256 key derived from the exact question and a separate
configuration namespace. The namespace incorporates the verified tenant
identity (when tenant mapping is configured), vector-store/table identity,
retrieval filters, embedding and LLM provider/model plus credential
fingerprints, prompts, history, output schema, reranker, and retrieval options.
Question text, credentials, and tenant names are not used as Redis key text or
written to cache logs. A supplied tenant header is not trusted; the existing
authenticated tenant context is used.

Cache errors are best-effort: Redis read/write failures are logged with only a
stable event name and exception type, then the request continues uncached. A
malformed or oversized cached value is treated as a miss. Values larger than
`DOCPIPE_RAG_CACHE_MAX_PAYLOAD_BYTES` are not stored, and all entries expire
after the configured TTL. There is no cache stampede lock, distributed
invalidation API, or cross-version schema guarantee; deployments should use a
short TTL during upgrades.

Cached values contain the generated answer, query, and citation/chunk payload.
Treat the Redis backend as sensitive data storage: restrict network access,
credentials, backups, and operator access accordingly. The cache is exact-match
only; it intentionally does not generalize semantically similar questions.
On a cache hit, response latency is the current cache lookup/request-pipeline
latency and token usage is unset; usage from the original generation is not
replayed as if it were incurred by the current request.
