
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class StartConversation:
    user_id: UUID

@dataclass(frozen=True)
class SendMessage:
    conversation_id: UUID
    content: str

