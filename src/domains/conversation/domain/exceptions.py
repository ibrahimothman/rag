class ConversationError(Exception):
    """Base exception for conversation-related errors."""
    pass


class InvalidTurnOrder(ConversationError):
    """Raised when the turn order is invalid."""
    pass

class EmptyUserMessage(ConversationError):
    """Raised when the user message is empty."""
    pass