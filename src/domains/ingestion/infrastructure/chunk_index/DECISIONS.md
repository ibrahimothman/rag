# Architectural Decisions — Chunk Index

This document records significant decisions for the chunk index component
of the Ingestion context. Each entry captures the decision, its context,
and what would trigger revisiting it.

---

## ADR-001: Storage — Postgres with pgvector

**Decision:** Use PostgreSQL with the pgvector extension as the chunk index
backend. Use the same Postgres instance as the project's main database
(jobs, library, conversation, etc.).

**Context:** The project's data access patterns (CRUD by ID, list by
foreign key, vector similarity at retrieval time) all fit a relational
database with vector extensions. Using one database for the whole project
significantly reduces operational complexity for a personal project.

**Consequences:** All data lives in one place — easier backups, no sync
issues between stores, transactions can span document and chunk operations
if ever needed. Migration to a dedicated vector store (Qdrant, Pinecone)
is possible later if scale demands it; would require swapping the
ChunkIndex implementation only.

**Revisit when:** Vector search latency becomes a bottleneck, or chunk
count grows beyond what pgvector handles efficiently (typically tens of
millions per index).

---

## ADR-002: Interface — Narrow, Document-Scoped

**Decision:** The ChunkIndex interface exposes only:
- `write_for_document(document_id, chunks)` — wholesale replace
- `remove_for_document(document_id)` — delete all chunks for a document

Search operations live in the Retrieval context with its own narrow
interface against the same physical store.

**Context:** Ingestion writes; Retrieval reads. Each context owns a
narrow view of the shared infrastructure. This keeps each context's
vocabulary and concerns clean, and prevents accidental cross-context
coupling.

**Consequences:** No `update_chunk()` or `query()` methods on the
ingestion-side interface. Adding capabilities requires deliberate decision
rather than incremental drift.

**Revisit when:** A genuine new ingestion-side need appears (e.g.,
inspecting existing chunks during a custom migration). Until then, the
narrowness is the feature.

---

## ADR-003: Write Semantics — Wholesale Replace per Document, Atomic

**Decision:** `write_for_document(document_id, chunks)` deletes all
existing chunks for the document and inserts the new chunks in a single
database transaction.

**Context:** Combined with the from-scratch retry model (ADR-004), this
gives document-level idempotency without requiring stable chunk IDs across
attempts. A retry simply replaces whatever the previous attempt left
behind. The transaction prevents observers from seeing a half-replaced
state.

**Consequences:**
- During a re-ingestion, search briefly sees zero chunks for the document
  while the transaction is in flight. Acceptable at current scale.
- Chunk IDs need not be stable across retries; uuid4 is fine.
- Failed partial writes leave no orphans; the next attempt cleans them up
  by virtue of the DELETE.

**Revisit when:** Concurrent re-ingestion-and-search becomes common enough
that the brief "no chunks" window is user-visible, or if chunk-level
idempotency becomes valuable for some new use case.

---

## ADR-004: Retry Strategy — From Scratch, No Resume (Deferred Optimization)

**Decision:** Failed ingestion jobs retry by running the entire pipeline
again from the beginning. Intermediate stage outputs (extracted text,
chunks before embedding) are not persisted. The job entity tracks attempt
count and stage but does not enable resumption from a failed stage.

**Context:** Resume-from-failed-stage would save work on retry, especially
for expensive stages (extraction of large PDFs, embedding API calls). It
would require:
- Persisting intermediate outputs after each stage
- Stage-aware pipeline logic (skip ahead based on job.stage)
- Cleanup policies for intermediate storage
- Versioning of intermediate outputs (chunks tied to chunker version)

This is real complexity to absorb without measured benefit.

**Why we're deferring:** Current usage patterns are unmeasured. We don't
yet know:
- How often retries happen in practice (transient embedding failures vs
  rare network blips)
- Which stage dominates ingestion cost (extraction? embedding API?)
- Whether re-running cheap stages on retry is a real cost or a rounding
  error

Speculative optimization without data is how projects accumulate
complexity that never pays off.

**Revisit when:** Production usage produces evidence that retry waste is
significant. Specifically:
- Embedding API costs are dominated by retry traffic
- Large-document extraction (OCR, long PDFs) is being repeated
  unnecessarily
- Retry latency makes user-facing experience visibly slow

At that point, decide between resume-from-stage (preserves work) or
adding caching at expensive stage boundaries (e.g., embedding cache keyed
by chunk hash). Both options leave the rest of the architecture
unchanged.

---

## ADR-005: Embedding Dimension — Fixed per Table

**Decision:** The chunks table declares one fixed embedding dimension at
creation time (`vector(N)` in pgvector). All chunks in the table share
that dimension. Changing the dimension requires a migration.

**Context:** This is not a pgvector quirk — it's universal across vector
stores:
- pgvector: `vector(N)` is fixed per column
- Chroma: dimension fixed per collection
- Qdrant: `vector_size` fixed per collection
- Pinecone: dimension fixed per index
- Weaviate: fixed per class

The reason is fundamental: similarity math (cosine, dot product, Euclidean)
is undefined between vectors of different dimensions. Vector stores
universally enforce one dimension per logical container.

**Consequences:**
- The chunk index is tied to the embedder's `embedding_size` config.
  Changing the embedder's output dimension requires a coordinated migration
  (new table or new column with the new dimension).
- The `embedding_model` column captures the model+dimension version
  (e.g., "gemini-embedding-2@1536") so chunks know which space they live
  in.

**Revisit when:** Multi-dimensional support is genuinely needed (e.g.,
A/B testing two embedding sizes simultaneously). At that point, options
are: separate tables per dimension, or accept full reindexing for any
change.

---

## ADR-006: Connection Ownership — Internal to Implementation

**Decision:** The PgVectorChunkIndex implementation owns its database
connection (or connection pool) internally. The pipeline, orchestration,
and domain layers know nothing about Postgres, psycopg, or any other DB
specifics.

**Context:** This preserves the boundary between domain and infrastructure.
Anything outside `infrastructure/chunk_index/pgvector.py` should be
swappable to a different storage backend with no changes.

**Consequences:**
- Connection management lives behind the ChunkIndex interface.
- Pooling, retry-on-disconnect, and other DB-specific concerns are
  internal details the implementation can evolve freely.
- The implementation receives connection config (DSN, pool size) at
  construction; orchestration doesn't see those details.

**Revisit when:** Cross-context transactions become necessary (e.g., a
single transaction spans both job repository and chunk index updates). At
that point, connection management may need to be externalized so multiple
components can share it. This is a real but distant concern.

---

## ADR-007: Schema Management — Alembic from the Start

**Decision:** Use Alembic to manage database schema and migrations. The
application does not run `CREATE TABLE` or any other DDL at runtime; the
schema is assumed to exist and is managed by Alembic migrations run as a
deployment/setup step.

**Context:** The project will have evolving schemas (chunks table,
ingestion jobs, library, eventually conversation tables). Alembic
provides:
- Versioned, ordered migration scripts
- Reproducible setup across environments
- Safe schema evolution that preserves data
- Industry-standard tooling for SQLAlchemy-based projects

The author has prior experience with Alembic, so the setup cost is low.

**Consequences:**
- Setup workflow: run migrations, then run the application.
- Schema changes are explicit, reviewed, and version-controlled.
- A learning curve avoided later (under pressure of a real migration).

**Revisit when:** Never expected to revisit; Alembic is appropriate at
all scales for relational schemas.

---

## ADR-008: Chunk IDs use UUID4

**Decision:** Chunks use uuid4() as primary key.

**Context:** UUID4 is random, which can cause B-tree index fragmentation
under high-frequency insert workloads. Our access patterns (batch insert
per document, no PK lookups in query paths) make this concern theoretical
for current scale. The vector index dominates insert cost regardless of
PK strategy.

**Revisit when:** Insert throughput becomes a bottleneck, or PK lookups
appear in hot paths. Migration path: switch to UUID7 (sequential UUIDs)
in the chunker — no schema change needed since both are stored as UUID.

---

## ADR-008: Vector Index Type — IVFFlat (Provisional)

**Decision:** Use IVFFlat as the vector index type on the `embedding`
column, with `lists = 100`.

```sql
CREATE INDEX ix_chunks_embedding ON chunks
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Context:** pgvector supports two vector index types:

- **IVFFlat** — clusters vectors into `lists` partitions; queries scan
  the nearest few clusters. Simpler, smaller, faster to build, but query
  recall depends on tuning (`lists` at build time, `probes` at query
  time).
- **HNSW** — hierarchical graph structure; better recall and query
  performance at scale, but slower to build, larger on disk, and more
  complex.

For initial development with a personal-scale dataset (thousands to
hundreds of thousands of chunks), IVFFlat is sufficient. It's the
historically more common choice and easier to reason about.

**Trade-offs being accepted:**

1. **Recall depends on `lists` and `probes`.** With `lists=100` and
   default `probes=1`, the query only scans 1 of 100 clusters. The
   nearest-neighbor result may miss true nearest vectors that landed in
   other clusters. Tuning `probes` higher improves recall at the cost of
   query latency.

2. **`lists` is set at build time and not auto-tuned.** The pgvector
   guidance is roughly `lists = rows / 1000` for up to 1M rows, then
   `lists = sqrt(rows)`. Our value of 100 is reasonable for ~100K rows
   but will be wrong if the table grows much larger or stays much smaller.
   Rebuilding the index is the only way to change it.

3. **Insert cost.** Every chunk insert updates the IVFFlat structure,
   adding the chunk to the nearest cluster. This is the dominant
   per-insert cost (compared to PK and document_id index updates). At
   small scale this is fine; at high insert rates it becomes a
   bottleneck.

4. **Build cost on existing data.** Building IVFFlat requires
   k-means-style clustering across all existing vectors. Fast for small
   tables; slow for large ones.

**What we are *not* deciding now:**

- Whether to use HNSW instead. It's a viable choice with different
  trade-offs (better recall, slower build, larger storage).
- Specific recall targets. We haven't measured retrieval quality yet.
- Query-time `probes` tuning. The default is conservative; raising it
  improves recall on every query.

**Revisit when:**

- **Retrieval quality feels poor** in real usage — the most likely first
  signal. Symptoms: questions whose answers are clearly in a document
  don't surface the relevant chunks. First mitigation: raise `probes` at
  query time. If that doesn't help enough, reconsider the index type or
  `lists` value.
- **The chunks table grows substantially** — past ~500K rows, `lists=100`
  is too small (clusters become too coarse). Rebuild with a higher
  `lists` value or switch to HNSW.
- **Insert throughput becomes a concern** — IVFFlat insert cost grows
  with `lists`. If insertion becomes a bottleneck and the cause is the
  vector index, options include reducing `lists` (worse recall), batch
  reindexing strategies, or evaluating HNSW.
- **Production traffic begins** — by this point the choice should be
  measurement-driven rather than provisional. Run side-by-side recall
  benchmarks of IVFFlat vs. HNSW against representative queries.

**Migration path:** switching index types is a single migration —
DROP the old index, CREATE the new one. Existing chunks don't change;
only the index is rebuilt. Brief downtime for queries during the
rebuild, but no data migration.

```sql
-- Migration to HNSW (when justified)
DROP INDEX ix_chunks_embedding;
CREATE INDEX ix_chunks_embedding ON chunks
USING hnsw (embedding vector_cosine_ops);
```

## How to Use This Document

When making a significant decision in this component, add a new ADR. Each
ADR should cover:

- **Decision** — what was decided, in one or two sentences
- **Context** — why this decision was needed, what alternatives were
  considered
- **Consequences** — what this implies, especially trade-offs
- **Revisit when** — concrete signals that would trigger reconsidering

Keep entries short and dated mentally — the *decision* matters more than
the prose. ADRs are reference material, not essays.