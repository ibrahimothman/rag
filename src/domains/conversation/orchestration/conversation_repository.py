from abc import ABC, abstractmethod
from uuid import UUID
from src.domains.conversation.domain import Conversation, UserMessage, AssistantMessage


class ConversationRepository(ABC):

    @abstractmethod
    def save(self, conversation: Conversation) -> None:
        """Save the conversation to the repository"""

    @abstractmethod
    def get(self, conversation_id: UUID) -> Conversation:
        """
        Get the conversation from the repository. 
        It raises 'ConversationNotFoundError' if not found
        """

    @abstractmethod
    def add_message(self, conversation_id: UUID, message: UserMessage | AssistantMessage) -> None:
        """Add a message to the conversation"""
        

class ConversationRepositoryError(Exception):
    """Raised by get() when a conversation_id is not found"""
    def __init__(self, message: str, *, permanent: bool):
        super().__init__(message)
        self.message = message
        self.permanent = permanentclass ConversationNotFoundError(Exception):
    
