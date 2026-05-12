# Generation Context — V1 Summary

## Overview

Generation is a **Supporting domain** responsible for producing grounded, cited answers from a question and retrieved source material. It receives a `GenerateAnswer` command carrying a question and grounding chunks (from Retrieval), calls a language model, streams the response back, resolves citation markers, and announces the outcome via events.

Generation is a **functional / stateless context**: it transforms input (question + grounding) into output (streamed answer + citations) without owning persistent state. Each generation operation is independent.

**Key relationships:**

- **Generation ↔ Conversation**: Open Host Service with Published Language. Generation provides a stable public API; Conversation and future consumers integrate against it without per-consumer accommodation.
- **Generation ↔ Retrieval**: Generation consumes Retrieval's output as grounding. Generation defines its own `GroundingChunk` type rather than importing Retrieval's types — identity-based reference via `chunk_id`.
- **Generation ↔ LLM Provider (Gemini)**: Anticorruption Layer. Vendor types, streaming protocol, error codes, and message formats never cross into the domain. Swapping providers means replacing one file.
- **Generation ↔ Analytics / Audit**: Open Host Service. Generation publishes events; observers subscribe without coupling.

**Subdomain classification:** Supporting overall. The LLM call itself is Generic (vendor-provided). Prompt engineering, citation handling, and hallucination prevention are local Core capabilities within a Supporting context — worth deeper investment in V2.

---

## Architecture

Same layered structure as Ingestion and Retrieval:

```
src/domains/generation/
├── api/                 # public contract (commands, events)
├── domain/              # value objects (Prompt, GroundingChunk, CitationMap, GroundingQuality)
├── stages/              # LLMCaller (concrete), GenerationModel (interface), pure functions
├── orchestration/       # GenerationPipeline, GenerationHandler
├── infrastructure/      # GeminiGenerationModel
└── composition.py       # wiring root

src/shared/gemini/       # shared Gemini client (used by Ingestion, Retrieval, Generation)
├── client.py            # GeminiClient, GeminiError
└── config.py            # GeminiClientConfig
```

### Layer Responsibilities

- **`api/`** — public contract. `GenerateAnswer` command, `GenerationStarted` / `AnswerChunk` / `GenerationCompleted` / `GenerationFailed` events. Stable across consumers.
- **`domain/`** — pure value objects: `GroundingChunk`, `Citation`, `Prompt`, `SystemInstructions`, `CitationEntry`, `CitationMap`, `GroundingQuality`. No aggregates (functional context). Contains real domain logic: `GroundingQuality.assess()` and `CitationMap.has_hallucinated_citations`.
- **`stages/`** — three components:
  - `GenerationModel` (abstract interface) — vendor-neutral: accepts `(system_instructions: str, user_content: str)`, streams `str` fragments
  - `LLMCaller` (concrete) — translates domain `Prompt` → neutral strings, calls `GenerationModel`, handles `GenerationModelError`
  - `construct_prompt()` and `resolve_citations()` — pure functions (not interfaces; no external dependencies to swap)
- **`orchestration/`** — `GenerationPipeline` (runs the prompt → stream → cite flow, emits events), `GenerationHandler` (thin command-to-pipeline entry point)
- **`infrastructure/`** — `GeminiGenerationModel` (vendor implementation of `GenerationModel`, uses shared `GeminiClient`)
- **`composition.py`** — `build_generation(config, gemini, event_subscribers)` returns a ready-to-use `GenerationHandler`

### Pipeline Flow

```
GenerateAnswer command
        │
        ▼
GenerationStarted ─────────────── PUBLIC event
        │
        ▼
[construct_prompt()] ──────────── INTERNAL — builds Prompt value object
        │
        ▼
[LLMCaller.call(prompt)] ──────── INTERNAL — translates Prompt → neutral strings
        │
        ▼
[GeminiGenerationModel.generate()] — vendor call via ACL
        │
        ▼
AnswerChunk × N ───────────────── PUBLIC stream (raw text with [chunk-N] markers)
        │
        ▼
[resolve_citations()] ─────────── INTERNAL — builds CitationMap
        │
        ▼
[GroundingQuality.assess()] ───── INTERNAL — derives quality signal
        │
        ▼
GenerationCompleted ───────────── PUBLIC terminal (full answer + citations + quality)

Or at any point:
        ↓
GenerationFailed ──────────────── PUBLIC terminal (reason + optional partial answer)
```

### Key Patterns Applied

- **Anticorruption Layer**: `GeminiGenerationModel` is the ACL boundary. Domain types on the outside; vendor types on the inside. `_format_contents()` and `_format_system_instructions()` are the translation methods.
- **Two-layer ACL**: `LLMCaller` translates domain → neutral strings; `GeminiGenerationModel` translates neutral strings → Gemini format. Swapping to OpenAI requires only replacing `GeminiGenerationModel`.
- **Streaming + accumulation**: one loop emits `AnswerChunk` events progressively and accumulates fragments into `full_answer` for post-stream citation resolution.
- **Functions over interfaces for pure logic**: `construct_prompt` and `resolve_citations` are module-level functions, not interfaces. No external dependencies to swap; no reason to mock. Interfaces only where polymorphism is needed (`GenerationModel`).
- **`GroundingQuality` as domain logic**: quality assessment (`GROUNDED` / `WEAK` / `UNGROUNDED` / `EMPTY_INPUT`) is explicit domain logic on the enum, not buried in the pipeline.
- **Shared Gemini client**: `GeminiClient` in `src/shared/gemini/` provides configured `genai.Client` and consistent error translation to all three Gemini adapters (Ingestion, Retrieval, Generation).
- **Two-ID correlation pattern**: `request_id` (from caller) + `generation_id` (from Generation) flow through all public events.

---

## ADRs

### ADR-1: Generation Is a Functional / Stateless Context

No `GenerationRecord` aggregate. Each generation is independent; state lives only in the event stream during the operation. Analytics and audit get what they need from subscribing to events. Simpler implementation; no Postgres table needed. Revisit if queryable generation history, retry-by-ID, or per-request state becomes a need.

### ADR-2: Two-Layer ACL for LLM Provider Integration

The vendor integration is split into two layers:
- `LLMCaller` (stages layer): translates domain `Prompt` → vendor-neutral `(system_instructions: str, user_content: str)`
- `GeminiGenerationModel` (infrastructure layer): translates neutral strings → Gemini-specific format

Neither layer knows all three languages (domain + neutral + vendor). `GeminiGenerationModel` knows nothing about `Prompt`, `SystemInstructions`, or `GroundingChunk`. Swapping to OpenAI or Anthropic replaces `GeminiGenerationModel` only; `LLMCaller` and all domain code are unaffected.

### ADR-3: V1 Streaming Is Synchronous and Blocking

`GenerationPipeline.run()` blocks the caller until the entire stream completes. All `AnswerChunk` events are emitted synchronously before the method returns. Simpler for V1; the full UX benefit of streaming (Conversation unblocking while tokens arrive) requires async infrastructure. See Hot Spot 1.

### ADR-4: Post-Stream Citation Resolution

Citations are resolved after streaming completes, not during. The stream contains raw text with `[chunk-N]` markers. After the last token, `resolve_citations()` scans the assembled text and builds a `CitationMap`. Reasons: citation markers can be split across stream chunks (making per-chunk resolution unreliable), and post-stream resolution avoids buffering delays during streaming.

### ADR-5: `GroundingQuality` as Domain Logic

Quality assessment lives on the `GroundingQuality` enum as `GroundingQuality.assess(citation_map, grounding_count)`. V1 heuristic: no grounding → `EMPTY_INPUT`, no citations → `UNGROUNDED`, citation coverage < 30% → `WEAK`, otherwise → `GROUNDED`. The 30% threshold is provisional and should be calibrated with measurement data.

### ADR-6: Functions Over Interfaces for Pure Logic

`construct_prompt` and `resolve_citations` are module-level functions, not abstract classes. Both are deterministic with no external dependencies. Making them interfaces would add ceremony without enabling any meaningful alternative implementation for V1. If variation becomes necessary (A/B testing prompt formats, alternative citation extraction), convert to interfaces then.

### ADR-7: `[chunk-N]` Citation Marker Format

V1 instructs the LLM via system prompt to cite sources using `[chunk-N]` notation where N is the chunk's 1-based index in the grounding list. `resolve_citations()` uses regex `\[chunk-(\d+)\]` to extract markers. Unresolved markers (LLM cited a non-existent chunk) are tracked in `CitationMap.unresolved_markers` as a hallucination signal.

### ADR-8: Shared Gemini Client

All three Gemini adapters share one `GeminiClient` from `src/shared/gemini/`. Centralises API key configuration, client construction, and error classification. Trade-off: creates code-level coupling between Ingestion, Retrieval, and Generation. Acceptable for a monolith; revisit if contexts split into separate services.

### ADR-9: `GroundingQuality` in `GenerationCompleted` Is Not a Failure Signal

All four `GroundingQuality` values (`GROUNDED`, `WEAK`, `UNGROUNDED`, `EMPTY_INPUT`) appear in `GenerationCompleted`, not `GenerationFailed`. These represent valid system outcomes where Generation completed its work. Only true system failures (LLM unreachable, stream interrupted, etc.) produce `GenerationFailed`. Consumers (Conversation) decide how to present quality signals to users.

### ADR-10: Mid-Stream Failure Emits `GenerationFailed` With Optional `partial_answer`

When the LLM stream is interrupted, `GenerationFailed` is emitted with the partial answer assembled so far in `partial_answer: str | None`. This allows Conversation to clear any already-displayed chunks. V1 does not introduce a separate `GenerationInterrupted` event — `GenerationFailed` with a non-None `partial_answer` carries enough signal. Revisit if UX testing shows partial answers are more valuable than a clean retry.

---

## Hot Spots

### Hot Spot 1: Synchronous Blocking Streaming

**Current:** `GenerationPipeline.run()` blocks until the stream completes. Conversation waits for the full generation. The `AnswerChunk` events are emitted, but the calling code doesn't return until done — partially defeating the UX benefit of streaming.

**V2 direction:** async streaming. `run()` becomes `async def run(...)`. `GenerationModel.generate()` becomes `async def generate(...) -> AsyncIterator[str]`. Conversation can handle the stream concurrently. Requires async infrastructure throughout.

**Migration path:** `Iterator[str]` → `AsyncIterator[str]` on `GenerationModel`. Pipeline becomes async. Handler follows. Domain and api layers are unaffected.

### Hot Spot 2: Structured Output Instead of Marker Parsing

**Current:** LLM embeds `[chunk-N]` markers in prose; regex extracts them post-stream. LLMs sometimes forget markers, use wrong format, or hallucinate citation numbers.

**V2 direction:** use Gemini's structured output (`response_schema`) to return `{"answer": str, "citations": list[{"chunk_index": int, "claim": str}]}`. No marker parsing. No regex. Reliable structured citations. Trade-off: structured output and streaming don't mix cleanly — may require dropping streaming for citation-heavy use cases.

### Hot Spot 3: Prompt Engineering and Grounding Rules

**Current:** `SystemInstructions` has four fields with simple string rules. No testing framework for prompts. Citation compliance depends entirely on instruction quality.

**V2 direction:** a proper prompt engineering practice — A/B testing instruction variants, measuring citation rate, measuring grounding compliance, measuring hallucination rate. The `SystemInstructions` value object is the right place to add this variability; the `GroundingQuality` signal is the measurement instrument.

### Hot Spot 4: Long Context Handling

**Current:** all grounding chunks are passed to the LLM regardless of total token count. Long documents or many chunks may exceed the model's context window.

**V2 direction:** token counting before the LLM call, chunk truncation or selection if context is too long, possibly a "compress grounding" step that summarises large chunks. The `Prompt` value object is the right place to add this logic.

### Hot Spot 5: Hallucination Detection and Validation

**Current:** `CitationMap.unresolved_markers` tracks markers the LLM produced that don't exist in the grounding (hallucinated citations). `GroundingQuality.UNGROUNDED` flags answers with no citations. But no detection of factual hallucination (LLM citing real chunks but misrepresenting their content).

**V2 direction:** a post-generation validation step that checks each cited claim against the cited chunk. Expensive (another LLM call) but powerful. Also: cross-encoder reranking of grounding chunks before generation to improve input quality.

### Hot Spot 6: Agentic V2 — Progress Streaming

**Current:** only `GenerationStarted`, `AnswerChunk`, `GenerationCompleted/Failed` are emitted. No visibility into what's happening between started and the first token.

**V2 direction (agentic RAG):** a third event type — progress events with agent identity and current task. Emitted as each agent (research agent, drafting agent, citation agent) begins and completes its work. Gives Conversation rich progress signals like "reading 3 sources," "drafting answer," "resolving citations." Current two-event-type architecture leaves room for this without breaking V1 consumers.

### Hot Spot 7: `GroundingQuality` Threshold Calibration

**Current:** the 30% coverage threshold in `GroundingQuality.assess()` is a V1 heuristic with no empirical basis.

**V2 direction:** measure the distribution of citation coverage across real queries. Plot `GROUNDED` vs `WEAK` vs `UNGROUNDED` rates. Calibrate the 30% threshold against user satisfaction signals. The threshold is a single constant in one method — cheap to tune once measurement data exists.

### Hot Spot 8: `GenerationQuality` as a Pipeline Quality Signal

The `grounding_quality` field in `GenerationCompleted` is both a user-facing signal and a system quality metric. Persistent `UNGROUNDED` or `WEAK` rates indicate upstream quality issues — weak Retrieval results, poor chunking strategy, or prompt instruction failures. A dashboard tracking `GroundingQuality` distribution over time is one of the most useful quality instruments for the entire RAG pipeline.

---

## Improvements

### Tier 1: Quality and Effectiveness

- **Structured output** — replace `[chunk-N]` marker parsing with Gemini's `response_schema`. Reliable citation extraction without regex. May require dropping streaming.
- **Prompt engineering framework** — A/B test instruction variants, measure citation rate and grounding compliance, tune `SystemInstructions` fields based on data.
- **Long context handling** — token counting before generation, chunk truncation/selection if context exceeds model limits.
- **Cross-encoder reranking of grounding** — reorder grounding chunks by relevance before passing to the LLM. Better input → better output.
- **Factual hallucination validation** — post-generation check that cited claims match cited chunks. Expensive but powerful.
- **Refusal quality** — tune the refusal rule in `SystemInstructions` to produce better "I don't know" messages when grounding is weak.

### Tier 2: Observability and Diagnosability

- **`GroundingQuality` dashboard** — track distribution over time as a whole-pipeline quality metric.
- **Citation coverage metrics** — `cited_chunks / total_chunks` per generation; flag low coverage as a quality signal.
- **Hallucination rate tracking** — `unresolved_markers / total_markers` per generation; proxy for LLM compliance with citation instructions.
- **Structured logging** — log every generation keyed by `generation_id` and `request_id` with `grounding_quality`, `duration_ms`, citation count.
- **Tracing** — propagate trace IDs through `LLMCaller`, `GeminiGenerationModel`, and streaming chunks. Full generation path visible in Jaeger/Honeycomb.
- **Per-stage timing** — how long does prompt construction take vs. LLM call vs. citation resolution? Identifies where latency lives.

### Tier 3: Resilience and Streaming

- **Async streaming** — `AsyncIterator[str]` on `GenerationModel`, async pipeline, async handler. Full non-blocking streaming for Conversation.
- **Streaming cancellation** — if Conversation stops listening (user closed the chat), signal the LLM stream to cancel. Saves quota and compute.
- **`GenerationInterrupted` event** — separate terminal event for mid-stream failures carrying `partial_answer`. Richer signal than `GenerationFailed` with a partial.
- **Retry with fresh generation** — if `GroundingQuality` is `UNGROUNDED`, automatically retry with a different prompt strategy before surfacing to the user. Bounded retries (like Ingestion's `RetryPolicy`).
- **Connection timeout** — explicit timeout on the LLM streaming call. Prevents indefinite hangs.

### Tier 4: Capability and Evolution

- **Agentic progress events** — third event type with agent identity and current task. Emitted by each agent in a multi-agent pipeline.
- **Multi-agent RAG orchestrator** — a dedicated `QuestionAnswering` context that coordinates Retrieval and Generation, grows intelligence (query rewriting, multi-step retrieval, tool use) without changing either context.
- **Tool use / function calling** — Generation calls external tools (web search, calculator, database lookup) as part of answer production. Requires `GenerationModel` to support Gemini's function calling API.
- **Multi-turn grounding** — incorporate conversation history as additional grounding context. Requires Conversation to pass relevant prior turns.
- **Multi-modal answers** — generate answers that include images, tables, or code blocks from the source documents.
- **Answer caching** — cache `GenerationCompleted` events keyed by `(question_hash, grounding_hash)`. Identical questions with identical grounding return cached answers instantly.

### Tier 5: Architectural Hygiene

- **Move citation format to configuration** — `[chunk-N]` is hardcoded in `construct_prompt` and `resolve_citations`. Make it a configurable parameter so different prompt strategies can use different formats.
- **`GenerationHandlerInterface`** — extract an abstract interface for the handler to simplify decorator composition (logging, metrics, auth).
- **Common cross-cutting decorators** — `LoggingGenerationHandler`, `MetricsGenerationHandler`. Same pattern as Ingestion.
- **`SystemInstructions` as configuration** — currently assembled in `construct_prompt` with default values. Should be configurable at composition time so different deployments can use different instructions without code changes.

### Tier 6: Future Context Integration

- **`QuestionAnswering` Orchestrator (V2)** — a dedicated context that coordinates Retrieval and Generation. Conversation delegates the RAG flow to it. The Orchestrator grows into agentic coordination while Conversation stays focused on chat experience. See architectural note below.
- **Conversation integration** — Conversation passes `RetrievalResult` chunks as `GroundingChunk`s in `GenerateAnswer`. The translation (Retrieval's `ScoredChunk` → Generation's `GroundingChunk`) lives in Conversation or the Orchestrator, not in either context.
- **Library integration** — when documents are deleted from Library, existing grounding based on those documents becomes stale. Generation could detect this via `document_id` in citations and flag affected answers.
- **Feedback loop** — user ratings on answers flow back through Conversation → Orchestrator as quality signals. `UNGROUNDED` answers that users rate poorly confirm the grounding pipeline needs improvement.

---

## Architectural Note: The Emerging `QuestionAnswering` Orchestrator

During V1 design, it became clear that Conversation was being asked to do two distinct jobs:

1. **Chat experience** — session management, message history, UI, follow-up questions
2. **RAG coordination** — calling Retrieval, translating results into grounding, calling Generation, handling streaming

These concerns have different change rates and different responsibilities. A dedicated **`QuestionAnswering` context** (working name) should own the coordination:

```
User question
     ↓
Conversation (chat experience — session, history, UI)
     ↓
QuestionAnswering Orchestrator (coordinates the answer flow)
  ├──→ Retrieval (finds relevant chunks)
  ├──→ Generation (produces grounded answer)
  └──→ returns Answer + Citations to Conversation
```

**Why this is the right direction:**

- Conversation stays focused on what it does well (chat UX, history, session)
- The Orchestrator is the natural home for growing RAG intelligence (query rewriting, multi-step retrieval, quality gates, agentic workflows)
- Each improvement to the RAG pipeline happens in one place without touching Conversation, Retrieval, or Generation
- Maps cleanly to DDD: Customer-Supplier (Orchestrator ↔ Retrieval, Orchestrator ↔ Generation), Open Host Service (Orchestrator ↔ Conversation)

**V1 plan:** build Conversation first to understand exactly what it needs. Then design and build the Orchestrator with both sides visible.

**V2 evolution:** the Orchestrator becomes an "Agentic RAG Orchestrator" — multi-step retrieval, quality assessment gates, tool use, multi-agent coordination — while Conversation and the domain contexts (Retrieval, Generation) remain unchanged.

---

## What V1 Delivers

A working Generation Context that:

- Receives `GenerateAnswer` commands with a question and grounding chunks
- Constructs a structured `Prompt` with system instructions (grounding rules, citation rules, refusal rules)
- Calls Gemini via a two-layer ACL (`LLMCaller` + `GeminiGenerationModel`)
- Streams `AnswerChunk` events progressively as tokens arrive
- Resolves `[chunk-N]` citation markers post-stream into a `CitationMap`
- Assesses `GroundingQuality` (grounded / weak / ungrounded / empty_input)
- Emits `GenerationCompleted` with full answer, citations, and quality signal
- Emits `GenerationFailed` with structured reason and optional partial answer
- Uses a shared `GeminiClient` with consistent error translation across all three Gemini adapters
- Is testable at every layer (domain, stages, pipeline, infrastructure, end-to-end)

The architecture supports every improvement above without rewrites. The ACL makes provider swapping a one-file change. The functional/stateless design keeps the context simple. The `GroundingQuality` signal connects Generation's output quality back to the Retrieval and Ingestion pipeline quality — making it a measurement instrument for the whole system.