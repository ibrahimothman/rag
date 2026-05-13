
from dataclasses import dataclass


from src.domains.conversation.infrastructure import PostgresConversationRepository, PostgresConversationRepositoryConfig
from src.domains.conversation.orchestration.handler import ConversationHandler
from src.shared.event_publishers import InMemoryEventPublisher
from src.domains.agent.orchestration.handler import AgentHandler


@dataclass(frozen=True)
class ConversationConfig:
    """Configuration for the Conversation system"""
    db_url: str
   
   
def build_conversation(
    config: ConversationConfig,
    agent: AgentHandler,
    event_subscribers: list | None = None,
) -> ConversationHandler:

    conversation_repository = PostgresConversationRepository(
        PostgresConversationRepositoryConfig(db_url=config.db_url)
    )
    event_publisher = InMemoryEventPublisher(
        subscribers=event_subscribers or [],
    )
    handler = ConversationHandler(
        conversation_repository, 
        event_publisher,
        agent,
    )
    return handler
