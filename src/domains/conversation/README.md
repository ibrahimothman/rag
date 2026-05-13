# Conversation Context — V1 Summary

## Overview

Conversation is the **Supporting domain** responsible for the user-facing chat experience. It manages conversation sessions, tracks message history, and coordinates with the QuestionAnswering Orchestrator to produce grounded answers. It is the only context that directly interacts with users.

Conversation is a **stateful context**: it owns a `Conversation` aggregate that accumulates messages over time. Unlike Retrieval and Generation (functional/stateless), Conversation persists state across sessions — a user can return to a conversation at any time and continue where they left off.

**Key relationships:**

- **Conversation ↔ QuestionAnswering Orchestrator**: Open Host Service with Published Language. Conversation explicitly calls the Orchestrator when a user sends a message. The Orchestrator provides a stable "answer my question" API. Conversation is the Customer; the Orchestrator is the Supplier.
- **Conversation ↔ Library (future)**: Customer-Supplier. Conversation will need document collection context from Library when personalizing retrieval.
- **Conversation ↔ User**: the human actor driving all commands.

**Subdomain classification:** Supporting. Standard chat UX patterns; competent engineering is sufficient for V1. Query rewriting and context management may emerge as Core capabilities in V2.

---

## Architecture

```
src/domains/conversation/
├── api/
│   ├── commands.py          # StartConversation, SendMessage
│   └── events.py            # seven public events
├── domain/
│   ├── conversation.py      # Conversation aggregate
│   └── message.py           # UserMessage, AssistantMessage, MessageRole
├── orchestration/
│   ├── handler.py           # ConversationHandler
│   └── conversation_repository.py  # interface + exceptions
├── infrastructure/
│   └── repository/
│       └── postgres.py      # PostgresConversationRepository
└── composition.py           # build_conversation()
```

### Layer Responsibilities

- **`api/`** — public contract. `StartConversation` and `SendMessage` commands. Seven events covering the full turn lifecycle.
- **`domain/`** — `Conversation` aggregate with turn-order invariants. `UserMessage` and `AssistantMessage` as distinct value objects (no unified `Message` type — they have structurally different fields).
- **`orchestration/`** — `ConversationHandler` coordinates the aggregate, Orchestrator, repository, and event publisher. `ConversationRepository` interface with append-only message semantics.
- **`infrastructure/`** — `PostgresConversationRepository` with two tables: `conversations` (metadata) and `conversation_messages` (append-only rows). Single JOIN query for loading conversations with messages.
- **`composition.py`** — `build_conversation(config, retrieval, generation, event_subscribers)` accepts pre-built handlers rather than building its own Gemini/DB dependencies.

### Turn Flow

```
SendMessage command received
        ↓
Load Conversation from repository
        ↓
add_user_message() → enforces turn order → UserMessage
        ↓
append_message() → persists UserMessage
        ↓
emit UserMessageReceived
        ↓
emit AnswerProcessing
        ↓
orchestrator.handle_process_question() → Response | None
        ↓
add_assistant_message() → enforces turn order → AssistantMessage
        ↓
append_message() → persists AssistantMessage
        ↓
emit AssistantMessageDelivered
        ↓
emit ConversationHistoryUpdated

Or on failure:
        ↓
emit ProcessingFailed
```

### Key Patterns Applied

- **Aggregate with lifecycle**: `Conversation` enforces turn-order invariants via `isinstance` checks on `last_message`. No double user messages; no assistant message without a preceding user message.
- **Append-only repository**: messages are never rewritten — each message is one INSERT. Conversation metadata saved once on creation. `get()` loads both via a single LEFT JOIN query.
- **Atomic position computation**: message `position` computed inside the INSERT via a subquery (`SELECT COALESCE(MAX(position), 0) + 1`) — no separate round trip, safe under concurrency.
- **Explicit Orchestrator call**: Conversation calls the Orchestrator directly rather than reacting to events. Synchronous request/response. Conversation controls when and how the Orchestrator is invoked.
- **`OrchestratorCitation` as Conversation's citation type**: Conversation uses the Orchestrator's vocabulary for citations rather than Generation's `CitationEntry`. Each context owns its language.
- **Two-table schema**: `conversations` for metadata, `conversation_messages` for the append-only message stream. Indexed by `conversation_id` for fast loading.

---

## ADRs

### ADR-1: No Conversation End State

Conversations persist indefinitely — no `ConversationEnded` event, no terminal state. Users can return to any conversation at any time. Archive and delete are V2 concerns. Implication: storage grows unboundedly; future versions will need archiving, expiry, or cold storage strategies.

### ADR-2: Append-Only Message Repository

Messages are never updated or deleted (V1). Each call to `append_message()` is one INSERT. This matches the domain's natural access pattern: messages are facts that accumulate. `save()` is called once at conversation creation; `append_message()` is called for every subsequent message. More efficient than rewriting the whole conversation on every message.

### ADR-3: Single JOIN Query for Loading

`get()` uses a LEFT JOIN between `conversations` and `conversation_messages` to load both in one round trip. `LEFT JOIN` (not `INNER JOIN`) handles empty conversations — a new conversation with no messages returns one NULL row which the loader filters out via `if row["message_id"] is not None`.

### ADR-4: Atomic Position via Subquery

Message `position` is computed inside the INSERT using a subquery:
```sql
(SELECT COALESCE(MAX(position), 0) + 1 FROM conversation_messages WHERE conversation_id = %s)
```
No separate count query, no race condition under concurrency. `COALESCE` handles the zero-messages case cleanly.

### ADR-5: Explicit Orchestrator Call — Not Event-Driven

Conversation explicitly calls `orchestrator.handle_process_question()` rather than subscribing to `UserMessageReceived` and reacting. Reasoning: Conversation owns the user experience — it decides when and how to invoke the Orchestrator. Some user messages may not need answering (future: commands, greetings). Explicit call gives Conversation control. Maps to Customer-Supplier: Conversation is the Customer, Orchestrator is the Supplier.

### ADR-6: Separate `UserMessage` and `AssistantMessage` Types

No unified `Message` type. `UserMessage` carries `content` and `timestamp`. `AssistantMessage` additionally carries `citations`, `grounding_quality`, and `generation_id`. Using one type with optional fields would produce `None` values that are conceptually wrong (a user message has no citations). The type system makes it impossible to ask for citations on a user message. Consistent with the `UserMessageReceived` / `AssistantMessageDelivered` event vocabulary.

### ADR-7: Turn-Order Invariants via `isinstance`

```python
def add_user_message(self):
    if isinstance(self.last_message, UserMessage):
        raise InvalidTurnOrder(...)

def add_assistant_message(self):
    if not isinstance(self.last_message, UserMessage):
        raise InvalidTurnOrder(...)
```

Single-line checks cover all cases (None, same-role, correct-role). The aggregate is the consistency boundary — no handler or repository logic needed for ordering enforcement.

### ADR-8: `OrchestratorCitation` as Citation Type in Conversation

Conversation stores and emits `OrchestratorCitation` (from the Orchestrator's domain) rather than `CitationEntry` (from Generation's api). Citations arrive in `Response.citations` from the Orchestrator — Conversation uses the Orchestrator's vocabulary directly rather than translating. Consistent with identity-based cross-context referencing.

### ADR-9: `ConversationConfig` Contains Only `db_url`

`build_conversation()` accepts pre-built `RetrievalHandler` and `GenerationHandler` rather than building them internally. `ConversationConfig` only needs `db_url` — what Conversation itself owns (its repository). Gemini credentials, model names, and embedding configuration belong to Retrieval and Generation, not Conversation. Same pattern as `build_question_answering` — accept handlers, own nothing.

### ADR-10: V1 Synchronous — No Answer Streaming to User

`AnswerChunkDelivered` is defined in the event vocabulary but not emitted in V1. The Orchestrator returns the full answer synchronously; Conversation emits `AssistantMessageDelivered` once with the complete answer. Streaming answer chunks to the user requires the Orchestrator to support async streaming. Deferred to V2.

---

## Hot Spots

### Hot Spot 1: Answer Streaming Not Implemented

`AnswerChunkDelivered` events are defined but never emitted. The user sees nothing until the full answer is ready. V2 direction: the Orchestrator gains streaming support, emits `OrchestratorAnswerChunk` events, Conversation subscribes and re-emits as `AnswerChunkDelivered`. Requires async infrastructure throughout.

### Hot Spot 2: `ConversationHistoryUpdated` Carries Full History

The event carries the entire message list on every turn. For long conversations this becomes expensive — the event grows with every message. V2: send only the delta (last turn) or a windowed context (last N turns). Also consider whether domain objects (`UserMessage | AssistantMessage`) should cross event boundaries — a flat serializable shape may be more appropriate.

### Hot Spot 3: History Truncation for Orchestrator

`history_for_context` currently returns all messages. For long conversations, this will exceed the LLM's context window. V2: implement windowing — last N turns, or a summarization step that compresses old history. The property exists now so the interface is stable; only the implementation changes.

### Hot Spot 4: `ConversationNotFoundError` Not Handled Gracefully

If `handle_send_message` is called with a nonexistent `conversation_id`, `ConversationNotFoundError` propagates to the caller uncaught. V2: return a typed error or emit a command-rejected event so callers can handle it gracefully without try/except.

### Hot Spot 5: No Progress Events Emitted

`AnswerProcessing` is emitted but there are no finer-grained progress signals during the Orchestrator's work. The user sees "processing" from the moment `SendMessage` is received until `AssistantMessageDelivered` fires — potentially several seconds with no feedback. V2: the Orchestrator emits `RetrievingContent` and `GeneratingAnswer` progress events; Conversation forwards them to the client.

### Hot Spot 6: Conversation Lifecycle — Archive and Delete

V1 has no archive or delete. Conversations persist forever. V2 needs:
- `ArchiveConversation` command → `ConversationArchived` event (soft archive, no new messages)
- `DeleteConversation` command → `ConversationDeleted` event (permanent, cascades to messages)
- `ConversationStatus` enum: `ACTIVE`, `ARCHIVED`, `DELETED`
- `add_user_message` and `add_assistant_message` should check status before accepting messages

### Hot Spot 7: Citations Serialized as JSONB

`OrchestratorCitation` is serialized to JSONB for storage. UUID fields are stored as strings (`str(uuid)`) and reconstructed on load (`UUID(str)`). If psycopg3 automatically decodes JSONB to Python objects (likely), `json.loads` on the read side is unnecessary. Test with `SELECT '[{"marker": "x"}]'::jsonb` and check `type(row["citations"])` to confirm.

### Hot Spot 8: No Feedback Collection

Users have no way to signal whether an answer was useful. This feedback is the most valuable signal for improving retrieval quality. V2: a `RateAnswer` command that records user feedback on specific `AssistantMessage`s. Aggregate over time to identify weak answers and trace back to retrieval/grounding quality issues.

---

## Improvements

### Tier 1: Streaming and Real-Time Experience

- **Implement `AnswerChunkDelivered` streaming** — Orchestrator gains async streaming support; Conversation re-emits chunks as `AnswerChunkDelivered` events; user sees answer appear progressively.
- **Progress events** — `AnswerProcessing` becomes richer; Conversation forwards Orchestrator progress events (`RetrievingContent`, `GeneratingAnswer`) as fine-grained status updates.
- **Cancellation** — user closes the chat mid-stream; Conversation signals the Orchestrator to cancel; stops wasting quota and compute.

### Tier 2: Conversation Lifecycle

- **Archive and delete** — `ArchiveConversation`, `DeleteConversation` commands with status enforcement in the aggregate.
- **Restore from archive** — re-activate an archived conversation.
- **Conversation expiry** — system-level cleanup of inactive conversations after a configurable period.
- **Cold storage** — move old conversation messages to cheaper storage; load on demand.

### Tier 3: History and Context

- **History windowing** — `history_for_context` returns last N turns instead of all messages. Prevents context window overflow for long conversations.
- **History summarization** — compress old history into a summary chunk. Passes the summary + recent turns instead of the full history.
- **Multi-turn query rewriting** — Conversation pre-processes user messages before passing to the Orchestrator. Resolves pronouns (*"what about that?"* → *"what about serializable isolation?"*), expands context from history.
- **Topic detection** — identify when a user changes topic mid-conversation; possibly start a new retrieval context rather than passing irrelevant history.

### Tier 4: Resilience and Correctness

- **Graceful `ConversationNotFoundError` handling** — return typed error or emit command-rejected event instead of propagating uncaught.
- **Idempotent message delivery** — `SendMessage` with the same content twice shouldn't produce duplicate turns. Add dedup key on commands.
- **Optimistic concurrency** — if two requests modify the same conversation simultaneously, detect and reject the conflict. Add `version` field to `Conversation`.
- **Connection timeout** — explicit timeout on Postgres connections in the repository.

### Tier 5: Quality and Feedback

- **`RateAnswer` command** — user rates an assistant message; stored on the conversation; feeds back into retrieval quality metrics.
- **Feedback aggregation** — aggregate ratings over time per document, per chunk, per generation strategy; surface as quality signals.
- **Answer regeneration** — user requests a new answer for the last question; Conversation re-invokes the Orchestrator without adding a new user message.
- **Source viewing** — user clicks a citation; Conversation fetches the source document page from Library and displays it.

### Tier 6: Observability

- **Structured logging** — every command and event logged with `conversation_id`, `message_id`, `user_id`.
- **Metrics** — messages per conversation, response latency, failure rate, grounding quality distribution.
- **Conversation analytics** — most common questions, topics, answer quality trends.
- **Session replay** — reconstruct a full conversation from its events for debugging.

### Tier 7: Future Context Integration

- **Library integration** — when a document is deleted from Library, citations in existing conversations become stale. Flag or remove affected citations.
- **User profile** — Conversation collects user preferences (language, tone, detail level) over time; passes them to the Orchestrator for personalized answers.
- **Notification** — when a conversation is inactive and a new document is indexed that's relevant to recent questions, notify the user.
- **Sharing** — export or share a conversation with citations as a document.

---

## What V1 Delivers

A working Conversation Context that:

- Starts conversations for users (`StartConversation` → `ConversationStarted`)
- Receives user messages, calls the Orchestrator, delivers grounded answers (`SendMessage` → full turn flow)
- Enforces strict turn-order discipline in the aggregate (no double messages, no answer without question)
- Persists conversation history in Postgres with append-only message semantics
- Loads conversations with a single JOIN query (one round trip)
- Emits seven events covering the full turn lifecycle for observability
- Uses the Orchestrator's citation vocabulary (`OrchestratorCitation`) consistently
- Handles processing failures gracefully with `ProcessingFailed` events
- Is testable at every layer (domain invariants, repository integration, end-to-end)

The architecture supports every improvement above without rewrites. The aggregate boundary is clean. The append-only repository is efficient and correct. The explicit Orchestrator call gives Conversation full control over the user experience. The event vocabulary is complete — V2 streaming requires implementing what's already named (`AnswerChunkDelivered`) rather than inventing new concepts.