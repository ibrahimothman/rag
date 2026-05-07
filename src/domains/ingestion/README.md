
Ingestion Context V1 — Summary and Improvements

## What V1 Is

A complete, layered, working system for ingesting documents into a searchable index. Built end-to-end with Domain-Driven Design and Clean Architecture, runs synchronously with bounded retries, and can be tested at every layer.

## The Architecture

```
api/                    Public contract — commands and events
domain/                 Business concepts, rules, invariants
stages/                 Abstract interfaces for pipeline steps
orchestration/          Use cases (handlers, pipeline)
infrastructure/         Concrete vendor implementations
composition.py          Wiring root
```

### What's In Each Layer

- **api/** defines what the outside world can ask Ingestion to do (commands: `IngestDocument`) and what Ingestion announces in return (events: `IngestionStarted`, `DocumentIndexed`, `IngestionFailed`).
- **domain/** holds the business concepts: `IngestionJob` (entity with lifecycle), `Chunk` and `EmbeddedChunk` (value objects), `JobStage` (the pipeline state machine), `FailureReason` and `FailureKind` (failure taxonomy with permanent/transient distinction), and `RetryPolicy` (the retry budget). Domain methods enforce rules: `advance_to` validates stage transitions, `mark_failed` records failures with the right kind, `retry` respects the policy.
- **stages/** defines four abstract interfaces — `Extractor`, `Chunker`, `Embedder`, `ChunkIndex` — plus their stage-specific exceptions (`ExtractionFailed`, `EmbeddingFailed`, `IndexingFailed`). Each carries a permanent flag for failure classification.
- **orchestration/** holds the use cases. `IngestionHandler` describes the use case in its simplest form: create a job, run the pipeline, persist state. `RetryingIngestionHandler` decorates the core handler with bounded-retry behavior. `Pipeline` is the reusable coordinator that runs jobs through stages, translating stage exceptions into `FailureReason` and emitting events.
- **infrastructure/** provides concrete implementations for each abstraction:
  - PlainTextExtractor and PdfExtractor (using PyMuPDF) for extraction
  - FixedSizeChunker for chunking
  - GeminiEmbedder for embedding (with RETRIEVAL_DOCUMENT task type and configurable dimensions)
  - PgVectorChunkIndex for vector storage (with wholesale-replace semantics per document)
  - PostgresJobRepository for job persistence (with upsert semantics)
  - InMemoryEventPublisher (Stage 1 — synchronous, in-process)
- Migrations managed by Alembic at the project root.
- Decisions captured in eight ADRs covering: storage choice, narrow interfaces, write semantics, retry strategy, embedding dimension constraints, connection ownership, schema management, and vector index choice.

## How the Pieces Cooperate

A request flows through:

1. Caller sends `IngestDocument` command
2. `RetryingIngestionHandler` invokes the core `IngestionHandler`
3. `IngestionHandler` creates a job, calls the `Pipeline`
4. `Pipeline` runs through stages: extract → chunk → embed → index
5. Each stage advances the job; failures translate to `FailureReason`
6. Stage events emitted via `InMemoryEventPublisher`
7. Pipeline returns; if job ended FAILED with retryable failure, `RetryingIngestionHandler` calls `job.retry()` and runs again
8. Eventually job is COMPLETED, FAILED with permanent failure, or out of retries

Stage failures are absorbed inside the pipeline. Infrastructure failures escape to the caller (script exits loudly).

## Testing Coverage

Each layer has its own test approach:

- **Domain tests:** pure logic, no infrastructure
- **Handler tests:** use fake Pipeline and JobRepository, verify use-case behavior
- **Retry handler tests:** programmable handler, mocked time.sleep, verify all retry paths
- **Infrastructure tests:** integration tests against real Postgres
- **End-to-end tests:** full system with real components


# Improvement Areas, by Value

## Tier 1 — Resilience and Production-Readiness

These are improvements that meaningfully change whether the system can run reliably under real conditions.

**Build a real worker loop**  
The current synchronous handler model works for one-off triggers. A long-running worker that polls for jobs (queued, retryable failures, stuck) using FOR UPDATE SKIP LOCKED enables genuine background processing without blocking callers. Most valuable when ingestion isn't tied to a user-facing action.

**Distinguish stage failures from infrastructure failures cleanly**  
Currently the pipeline absorbs _StageFailure and lets infrastructure errors propagate. The distinction is implicit. Making it explicit (e.g., StageFailed vs. InfrastructureFailed exception types) clarifies recovery responsibilities and lets the worker layer handle infrastructure outages distinctly from per-job failures.

**Add stuck-job recovery**  
Once a worker exists, it should pick up jobs idle in non-terminal stages (updated_at older than threshold). Without this, a worker crash mid-pipeline orphans jobs forever. The data model already supports it — needs query and worker logic.

**Honor server-specified retry timing**  
Some APIs return Retry-After headers. Respecting these when present is more polite to the upstream and produces more predictable retry behavior than fixed/exponential client-side backoff.

**Exponential backoff with cap**  
Currently retries use a fixed backoff. Exponential backoff (capped) adapts better to the actual recovery time of various transient failures, especially with RetryPolicy.max_attempts greater than 3.

---

## Tier 2 — Observability and Diagnosability

Improvements that make the system's behavior visible and debuggable, especially under failure.

**Production-grade FailureReason**  
Current shape: stage, kind, message. Production version: add code (stable identifier like EMBEDDING_RATE_LIMIT), category (operational taxonomy), correlation_id (distributed tracing), retry_after (server hint), metadata (stage-specific context). This unlocks structured monitoring, alerting per code, and queryable failure analytics.

**Distinct IngestionAbandoned event**  
Replace the predictive will_retry field on IngestionFailed with a separate event that fires only when the job is truly given up on. Subscribers get clean facts instead of forecasts that may not come true.

**Structured logging across the stack**  
Logs as structured records (JSON or similar) keyed by job_id, document_id, stage. Enables grep-friendly debugging and feeds log aggregation systems naturally.

**Metrics interface**  
A no-op metrics interface today, swappable for Prometheus/StatsD later. Counters per failure code, histograms per stage timing, gauges per worker health. Most valuable once monitoring dashboards exist.

**Tracing**  
Inject a trace ID at the command boundary, propagate through stages and downstream calls. Lets operators see a single ingestion's full path in tools like Jaeger or Honeycomb.

---

## Tier 3 — Performance and Cost

Improvements that reduce time, money, or compute spent.

**Embedding cache**  
Cache embeddings keyed by hash(chunk_text + model_version + task_type). Avoids re-embedding identical chunks across reingestion or retries. Saves API calls and money. Easy to add as a CachingEmbedder decorator.

**Resume-from-stage on retry**  
Persist intermediate stage outputs (extracted text, chunks). On retry, skip stages that already succeeded. Major saving for expensive operations (large PDF extraction, batches of embeddings) when failures are stage-specific rather than system-wide.

**Connection pooling**  
Each repository call opens a new connection. A pool would amortize connection setup over many calls. Most valuable at higher request rates.

**HNSW vector index instead of IVFFlat**  
HNSW typically delivers better recall at retrieval time and better insert performance at scale. IVFFlat was a starting choice; switching is a one-line index rebuild.

**Async pipeline**  
For workers handling many concurrent ingestions, async would let one process multiplex I/O across jobs. Significant code change; only valuable when concurrency demands exceed what multiple sync workers can provide.

---

## Tier 4 — Correctness and Robustness

Improvements that close edge cases or harden the system against rare failures.

**Atomic job claim with FOR UPDATE SKIP LOCKED**  
Once multiple workers exist, the pickup query needs locking to prevent two workers from running the same job. Standard pattern with Postgres.

**Connection timeouts everywhere**  
DB connect, embedding API calls, anything network-bound. Prevents indefinite hangs. Already added to DSN; should be consistent across all infrastructure components.

**Versioned chunking strategy enforcement**  
Currently chunks store their chunking_strategy_version, but nothing prevents chunks from different versions coexisting in the index. A check at query time, or a constraint, would prevent silent quality drift.

**Source location lookup for retries**  
Currently the retry stores the command in memory. If the worker dies and a new worker picks up the job, the source location isn't on the entity. Either persist it on the job or look it up from Library. Becomes important once async workers exist.

**Validation of embedding dimension at startup**  
At composition time, verify that the embedder's configured dimension matches the chunk index's table dimension. Catches misconfiguration before any document is processed.

**Idempotency of event publishing**  
If a subscriber takes side effects (sends notifications, calls APIs), retries can produce duplicate effects. Eventual outbox pattern with dedup keys mitigates this.

---

## Tier 5 — Architectural Hygiene

Improvements that don't change behavior but make the codebase easier to reason about and evolve.

**Extract IngestionHandlerInterface**  
Currently `IngestionHandler` is concrete. Making it an interface would simplify decorator composition (retry, logging, metrics, etc.) and make handler-level test fakes cleaner.

**Common cross-cutting decorators**  
`LoggingIngestionHandler`, `MetricsIngestionHandler`, `AuthorizingIngestionHandler` — each adds one concern, composable in the composition root. Most valuable once multiple concerns exist.

**Generalize the failure classification**  
Move `permanent: bool` to a `FailureKind` enum at the stage level, mirroring the domain. Stage exception construction becomes more uniform.

**SourceFetcher abstraction**  
Currently extractors read local file paths directly. A `SourceFetcher` abstraction (with `LocalFileFetcher`, `S3Fetcher`, `URLFetcher` implementations) would decouple extractors from source storage. Most valuable when sources stop being local-only.

**Schema column ordering and explicit SELECTs**  
Use explicit column lists in queries instead of `SELECT *`, and use `dict_row` for safe attribute access. Already the convention; consistent application closes the loop.

**Better separation of Chunk and EmbeddedChunk versions**  
`chunking_strategy_version` is on `Chunk`, `embedding_model_version` on `EmbeddedChunk`. The split is correct but worth documenting clearly so future readers don't second-guess.

---

## Tier 6 — Capability and Evolution

Improvements that extend what the system can do, not just how well it does the existing work.

**More extractors**  
Image OCR, audio transcription, video, structured documents (Word, Excel). Each is a new `Extractor` implementation; pipeline doesn't change.

**Smarter chunking strategies**  
`SemanticChunker` (sentence/paragraph aware), `HierarchicalChunker` (preserves structure), domain-specific chunkers for code or tables. Each is a new `Chunker` implementation.

**Multiple chunking strategies per document type**  
A `ChunkerSelector` that routes to the right strategy based on document type. Useful when document corpus is heterogeneous.

**Alternative embedding providers**  
Local models (`Sentence Transformers`), other cloud providers (Cohere, Voyage). Each is a new `Embedder` implementation. Fallback chains (try Gemini, fall back to local on outage) become possible with a `FallbackEmbedder` decorator.

**Multi-modal embeddings**  
Once Gemini Embedding 2 is fully wired in, supporting image and audio embeddings requires extending the chunk shape to carry non-text content references.

**Multiple embedding dimensions concurrently**  
A/B testing different dimensions, or separate indexes for different recall/cost trade-offs. Requires schema rework (separate tables/columns per dimension).

**Reingestion with new model versions**  
A use case that takes a document, drops its chunks, reprocesses with current models. The `ReingestDocument` command was sketched but never wired. Most valuable when models or strategies change frequently.
