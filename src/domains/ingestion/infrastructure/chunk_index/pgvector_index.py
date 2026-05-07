from ...stages.chunk_index import ChunkIndex, IndexingFailed
from uuid import UUID
from ...domain.chunk import EmbeddedChunk
from dataclasses import dataclass

import psycopg
from psycopg.types.json import Json
from pgvector.psycopg import register_vector
from psycopg.errors import (
    OperationalError,
    InterfaceError,
    UndefinedTable,
    UndefinedColumn,
    DataError
)

# TODO: does uuid4 helps?

@dataclass(frozen=True)
class PgVectorChunkIndexConfig:
    db_url: str

class PgVectorChunkIndex(ChunkIndex):

    """
    Stores embedded chunks in PostgreSQL with pgvector.
    
    Uses wholesale-replace semantics: write_for_document() deletes existing
    chunks for the document and inserts the new ones atomically. Failed
    partial attempts leave no orphans because the next attempt deletes
    them as part of its replacement.
    """

    def __init__(self, config: PgVectorChunkIndexConfig):
        self._config = config

    def write_for_document(self, document_id: UUID, chunks: list[EmbeddedChunk]) -> None:

        """
        Replace all chunks for the document with the given chunks atomically.
        
        """

        try:
            with psycopg.connect(self._config.db_url) as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    self._delete_existing(cur, document_id)
                    if chunks:
                        self._insert_many(cur, document_id, chunks)
                    
        except (OperationalError, InterfaceError) as e:
            raise IndexingFailed(
                f"Database connection error: {e}",
                permanent=False
            )
        except (UndefinedTable, UndefinedColumn) as e:
            raise IndexingFailed(
                f"Database schema error: {e}",
                permanent=True
            )

        except DataError as e:
            raise IndexingFailed(
                f"Data error: {e}",
                permanent=True
            )

    def remove_for_document(self, document_id: UUID) -> None:
        try:
            with psycopg.connect(self._config.db_url) as conn:
                with conn.cursor() as cur:
                    self._delete_existing(cur, document_id)
        except (OperationalError, InterfaceError) as e:
            raise IndexingFailed(
                f"Database connection error: {e}",
                permanent=False
            )
        except (UndefinedTable, UndefinedColumn) as e:
            raise IndexingFailed(
                f"Database schema error: {e}",
                permanent=True
            )
        except DataError as e:
            raise IndexingFailed(
                f"Data error: {e}",
                permanent=True
            )
    def _delete_existing(self, cur, document_id: UUID) -> None:
        cur.execute("""
        DELETE FROM chunks
        WHERE document_id = %s
        """, (document_id,))

    def _insert_many(self, cur, document_id: UUID, chunks: list[EmbeddedChunk]) -> None:
        
        data = [
            (
                chunk.chunk.id, 
                document_id, 
                chunk.chunk.text, 
                chunk.chunk.position, 
                chunk.vector, 
                chunk.chunk.chunking_strategy_version,
                chunk.embedding_model_version, 
                Json(chunk.chunk.metadata)
            )
            for chunk in chunks
        ]
        cur.executemany("""
        INSERT INTO chunks (chunk_id, document_id, text, position, embedding, chunking_strategy, embedding_model, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, data)