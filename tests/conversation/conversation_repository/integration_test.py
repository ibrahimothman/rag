import pytest
import os
from dotenv import load_dotenv

from src.domains.conversation.infrastructure import (
    PostgresConversationRepository,
    PostgresConversationRepositoryConfig
)
from src.domains.conversation.domain import Conversation, UserMessage, AssistantMessage
from src.domains.conversation.orchestration.conversation_repository import ConversationNotFoundError
from src.domains.agent.domain.response import CitationEntry
from src.domains.agent.domain.grounding import Citation
from uuid import uuid4
from datetime import datetime


load_dotenv()
TEST_DB_URL = os.environ.get("TEST_DB_URL")



@pytest.fixture(autouse=True)
def clean_db(repo):
    """Clean test data before each test."""
    yield
    # cleanup after — delete any test conversations
    # simplest: truncate in teardown (test DB only!)
    import psycopg
    with psycopg.connect(TEST_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM conversation_messages WHERE TRUE")
            cur.execute("DELETE FROM conversations WHERE TRUE")

@pytest.fixture
def repo():
    if TEST_DB_URL is None:
        pytest.skip(reason="TEST_DB_URL not set")
    return PostgresConversationRepository(
        PostgresConversationRepositoryConfig(db_url=TEST_DB_URL)
    )

@pytest.mark.integration
class TestPostgresConversationRepository:
    def test_save_and_get_empty_conversation(self, repo):
        """
        Save a new conversation and load it back.
        Empty conversation has no messages.
        """

        conversation = Conversation.start(user_id=uuid4())

        repo.save(conversation)
        
        loaded = repo.get(conversation.id)
        assert loaded.id == conversation.id
        assert loaded.user_id == conversation.user_id
        assert loaded.messages == []

    def test_raise_when_not_found(self, repo):
        """
        Raises ConversationNotFoundError when conversation is not found.
        """
        with pytest.raises(ConversationNotFoundError):
            repo.get(uuid4())

    def test_append_and_load_messages(self, repo):
        """
        Append a message to the conversation and load it back.
        """
        conversation = Conversation.start(user_id=uuid4())
        repo.save(conversation)
        
        user_message = conversation.add_user_message(content="what is serializable isolation?")
        repo.add_message(conversation.id, user_message)

        
        citations = (
            CitationEntry(
                marker="chunk-1",
                chunk_id="chunk-1",
                citation=Citation(
                    document_id=uuid4(),
                    page=1
                )
            ),
        )
        assistant_message = conversation.add_assistant_message(
            content="Serializable isolation is the strongest...", 
            citations=citations, 
            grounding_quality="grounded"
        )
        repo.add_message(conversation.id, assistant_message)

        loaded = repo.get(conversation.id)
      
        assert len(loaded.messages) == 2

        # Verify user message
        loaded_user = loaded.messages[0]
        assert isinstance(loaded_user, UserMessage)
        assert loaded_user.content == "what is serializable isolation?"
        assert loaded_user.id == user_message.id

        # Verify assistant message
        loaded_assistant = loaded.messages[1]
        assert isinstance(loaded_assistant, AssistantMessage)
        assert loaded_assistant.content == "Serializable isolation is the strongest..."
        assert loaded_assistant.grounding_quality == "grounded"
        assert len(loaded_assistant.citations) == 1
        assert loaded_assistant.citations[0].marker == "chunk-1"
        assert loaded_assistant.citations[0].citation.page == 1

        