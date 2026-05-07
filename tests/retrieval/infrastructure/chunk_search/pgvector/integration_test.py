# tests/retrieval/infrastructure/chunk_search/pgvector/integration_test.py
"""
Integration test for PgVectorChunkSearch against a real Postgres + pgvector.

Inserts a known chunk into the chunks table, runs a search with a known
embedding, verifies the chunk is returned with a meaningful score.

Requires:
- A running Postgres with pgvector extension enabled
- The chunks table created (via Alembic migrations)
- A test database (different from your dev/prod DB)

Set RETRIEVAL_TEST_DB_URL environment variable to the test DB connection string.
"""
import os
import pytest
import psycopg
from pgvector.psycopg import register_vector
from uuid import uuid4
from uuid import UUID
import dotenv
from pathlib import Path


from src.domains.retrieval.infrastructure.chunk_search.pgvector import (
    PgVectorChunkSearch,
    PgVectorChunkSearchConfig,
)
from src.domains.retrieval.domain.query import Query, EmbeddedQuery


dotenv.load_dotenv()
TEST_DB_URL = os.environ.get("RETRIEVAL_TEST_DB_URL")

current_dir = Path(__file__).parent
CHUNKS_FILE = current_dir / "test_chunks.txt"

@pytest.fixture
def chunks():

    with open(CHUNKS_FILE, "r") as f:
        content = f.read()
        return [c.strip() for c in content.split('---') if c.strip()]


def _make_chunks_bulk(document_id: UUID, chunks: list[str]) -> list[tuple]:
    return [
        (
            uuid4(), 
            document_id,
            c, 
            i,
            [0.1] * 1536,
            "fixed_size_v1",
            "test-model@1536",
            "{}"
        ) 
        for i, c in enumerate(chunks)
    ]

@pytest.mark.skipif(
    TEST_DB_URL is None,
    reason="RETRIEVAL_TEST_DB_URL not set; skipping integration test",
)
def test_finds_inserted_chunk_by_similar_vector(chunks):
    """
    End-to-end: insert a chunk, search with the same vector, verify
    the chunk is returned with a high score.
    """
    # Fixed embedding for predictable testing
    embedding = [0.1] * 1536
    document_id = uuid4()
    
    chunks = _make_chunks_bulk(document_id, chunks)



    
    # Insert a known chunk directly
    with psycopg.connect(TEST_DB_URL) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            # Clean state
            cur.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))
            
            # Insert one chunk
            cur.executemany("""
                INSERT INTO chunks (chunk_id, document_id, text, position, embedding, chunking_strategy, embedding_model, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, chunks)
        conn.commit()
    
    # Search using the SAME vector — should be a perfect match
    search = PgVectorChunkSearch(PgVectorChunkSearchConfig(db_url=TEST_DB_URL))
    
    query = EmbeddedQuery(
        query=Query(text="What does PACELC stand for?"),
        vector=embedding,
        embedding_model_version="test-model@1536",
    )
    
    results = search.find_similar_chunks(query, limit=5)
    
    # Assertions
    assert len(results) >= 1
    
    
    matched = results[0]
    assert matched.citation.document_id == document_id
    
    # Same vector → similarity should be ~1.0 (perfect match)
    assert matched.score > 0.9, (
        f"Identical embeddings should produce score near 1.0, got {matched.score}"
    )
    
    # Cleanup
    with psycopg.connect(TEST_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))
        conn.commit()