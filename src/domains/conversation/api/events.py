from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from src.domains.agent.domain import CitationEntry
from src.domains.conversation.domain import UserMessage, AssistantMessage


@dataclass(frozen=True)
class ConversationStarted:
    conversation_id: UUID
    user_id: UUID
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass(frozen=True)
class UserMessageReceived:
    conversation_id: UUID
    message_id: UUID
    content: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass(frozen=True)
class AnswerProcessing:
    conversation_id: UUID
    message_id: UUID      # the user message being answered
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass(frozen=True)
class AnswerChunkDelivered:
    conversation_id: UUID
    message_id: UUID      # the assistant message being built
    sequence: int
    text: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass(frozen=True)
class AssistantMessageDelivered:
    conversation_id: UUID
    message_id: UUID
    content: str
    citations: tuple[CitationEntry, ...]
    grounding_quality: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass(frozen=True)
class ConversationHistoryUpdated:
    conversation_id: UUID
    turn_count: int
    messages: tuple[UserMessage | AssistantMessage, ...]

@dataclass(frozen=True)
class ProcessingFailed:
    conversation_id: UUID
    message_id: UUID      # which user message failed
    reason: str           # technical reason (not user-facing)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))