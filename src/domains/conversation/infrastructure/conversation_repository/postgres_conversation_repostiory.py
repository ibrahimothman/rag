from src.domains.conversation.orchestration.conversation_repository import ConversationRepository, ConversationNotFoundError, ConversationRepositoryError
from src.domains.conversation.domain import Conversation, UserMessage, AssistantMessage
from src.domains.agent.domain import Citation, CitationEntry
from uuid import UUID
from dataclasses import dataclass

# TODO: we are using the agent's domain, bad!
# TODO: citations is nested json, how can we handle this?

import psycopg
from psycopg.errors import (
    OperationalError,
    InterfaceError,
    UndefinedTable,
    UndefinedColumn,
    IntegrityError,
    DataError
)
from psycopg.rows import dict_row
from psycopg.types.json import Json



@dataclass(frozen=True)
class PostgresConversationRepositoryConfig:
    db_url: str


class PostgresConversationRepository(ConversationRepository):
    def __init__(self, config: PostgresConversationRepositoryConfig):
        self._config = config

    def save(self, conversation: Conversation) -> None:
        command = """
        INSERT INTO conversations (
            id, user_id, started_at, updated_at
        )
        VALUES (%s, %s, %s, %s)
        """
        params = (
            conversation.id, 
            conversation.user_id, 
            conversation.started_at, 
            conversation.updated_at
        )
        self._insert_one(command, params)

    def get(self, conversation_id: UUID) -> Conversation:
        rows = self._fetch_all(
            """
            SELECT 
                c.id as conversation_id, c.user_id, c.started_at, c.updated_at,
                m.id as message_id, m.role, m.content, m.grounding_quality, m.citations, m.timestamp, m.position
            FROM conversations c
            LEFT JOIN conversation_messages m
                ON c.id = m.conversation_id
            WHERE c.id = %s
            ORDER BY m.position ASC
            """,
            (conversation_id,)
        )

        if not rows:
            raise ConversationNotFoundError(f"Conversation not found: {conversation_id}")
        
        first = rows[0]

        
        return Conversation(
            id=first["conversation_id"],
            user_id=first["user_id"],
            started_at=first["started_at"],
            updated_at=first["updated_at"],
            messages=[self._row_to_message(row) for row in rows if row["message_id"] is not None]
            
        )

    def add_message(self, conversation_id: UUID, message: UserMessage | AssistantMessage) -> None:

        grounding_quality = message.grounding_quality if isinstance(message, AssistantMessage) else None
        

        citations = (
            Json([
                {
                    "marker": citation.marker,
                    "chunk_id": str(citation.chunk_id),
                    "document_id": str(citation.citation.document_id),
                    "page": citation.citation.page
                }
                for citation in message.citations
            ])
            if isinstance(message, AssistantMessage) and message.citations
            else None
        )

        command = """
        INSERT INTO conversation_messages (
            id, conversation_id, role, content,
            grounding_quality, citations, timestamp,
            position
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 
        (SELECT COALESCE(MAX(position), 0) + 1
        FROM conversation_messages
        WHERE conversation_id = %s)
        
        )
        """
        params = (
            message.id, 
            conversation_id, 
            message.role,
            message.content, 
            grounding_quality,
            citations,
            message.timestamp,
            conversation_id,
        )
        self._insert_one(command, params)


    def _insert_one(self, sql: str, params: tuple) -> None:
        try:
            with psycopg.connect(self._config.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
        except (OperationalError, InterfaceError) as e:
            raise ConversationRepositoryError(f"Database connection error: {e}", permanent=False)
        except (UndefinedTable, UndefinedColumn) as e:
            raise ConversationRepositoryError(f"Schema error: {e}", permanent=True)
        except IntegrityError as e:
            raise ConversationRepositoryError(f"Integrity violation  : {e}", permanent=True)
        except DataError as e:
            raise ConversationRepositoryError(f"Data error: {e}", permanent=True)

    def _fetch_all(self, sql: str, params: tuple) -> list[dict]:
        try:
            with psycopg.connect(self._config.db_url) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params)
                    return cur.fetchall()
        except (OperationalError, InterfaceError) as e:
            raise ConversationRepositoryError(f"Database connection error: {e}", permanent=False)
        except (UndefinedTable, UndefinedColumn) as e:
            raise ConversationRepositoryError(f"Schema error: {e}", permanent=True)



    def _row_to_message(self, row: dict) -> UserMessage | AssistantMessage:
        if row["role"] == "user":
            return UserMessage(
                id=row["message_id"],
                conversation_id=row["conversation_id"],
                content=row["content"],
                timestamp=row["timestamp"]
            )

        citations = tuple(
            CitationEntry(
                marker=citation["marker"],
                chunk_id=citation["chunk_id"],
                citation=Citation(
                    document_id=citation["document_id"],
                    page=citation["page"]
                )
            )
            for citation in (row["citations"] if row["citations"] else [])
        
        )    

        return AssistantMessage(
            id=row["message_id"],
            conversation_id=row["conversation_id"],
            content=row["content"],
            grounding_quality=row["grounding_quality"],
            citations=citations,
            timestamp=row["timestamp"]
        )