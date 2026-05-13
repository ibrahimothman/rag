from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from uuid import uuid4
from src.domains.conversation.domain.exceptions import InvalidTurnOrder
from datetime import timezone

from src.domains.agent.domain import CitationEntry

# TODO: Conversation uses the agent's domain, bad!

@dataclass(frozen=True)
class UserMessage:
    id: UUID
    conversation_id: UUID
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def role(self) -> str:
        return "user"

@dataclass(frozen=True)
class AssistantMessage:
    id: UUID
    conversation_id: UUID
    content: str
    grounding_quality: str
    citations: tuple[CitationEntry, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def role(self) -> str:
        return "assistant"

@dataclass
class Conversation:
    id: UUID
    user_id: UUID
    messages: list[UserMessage | AssistantMessage]
    started_at: datetime
    updated_at: datetime


    @classmethod
    def start(cls, user_id: UUID) -> "Conversation":
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            user_id=user_id,
            messages=[],
            started_at=now,
            updated_at=now,
        )

    def add_user_message(self, content: str) -> UserMessage:
        if isinstance(self.last_message, AssistantMessage):     
            raise InvalidTurnOrder("Cannot add user message — assistant has already responded, expecting user input")
        now = datetime.now(timezone.utc)
        message = UserMessage(
            id=uuid4(),
            conversation_id=self.id,
            content=content,
        )
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)
        return message

    def add_assistant_message(
        self,
        content: str,
        citations: tuple,
        grounding_quality: str,
    ) -> AssistantMessage:

    
        if not isinstance(self.last_message, UserMessage):
            raise InvalidTurnOrder("Cannot add assistant message — no preceding user message")

        message = AssistantMessage(
            id=uuid4(),
            conversation_id=self.id,
            content=content,
            citations=citations,
            grounding_quality=grounding_quality,
        )
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)
        return message

    @property
    def history_for_context(self) -> tuple:
        return tuple(self.messages)
    
    @property
    def turn_count(self) -> int:
        return sum(1 for _ in self.messages if isinstance(_, UserMessage))

    @property
    def last_message(self) -> UserMessage | AssistantMessage:
        return self.messages[-1] if self.messages else None