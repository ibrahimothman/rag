import pytest
from .pgvector import PgVectorChunkIndex, PgVectorChunkIndexConfig
from ...domain.chunk import EmbeddedChunk, Chunk
from uuid import uuid4

import psycopg

TEST_DB_URL = "postgresql://postgres:postgres@localhost:5432/rag-app"

@pytest.fixture
def index():
    config = PgVectorChunkIndexConfig(db_url=TEST_DB_URL)
    return PgVectorChunkIndex(config)


@pytest.fixture(autouse=True)
def cleanup():
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.execute("TRUNCATE TABLE chunks")
    yield    
            
    

def _create_chunk(document_id, position) -> EmbeddedChunk:
    
    chunk = Chunk(
        id=uuid4(),
        text=f"Chunk {position}",
        source_document_id=document_id,
        position=position,
        metadata={}
    )
    return EmbeddedChunk(
        chunk=chunk,
        vector=[0.1] * 1536,
        embedding_model_version="gemini-embedding-2@1536"
    )

def test_write_chunks_for_document(index):

    document_id = uuid4()
    chunks = [_create_chunk(document_id=document_id, position=i) for i in range(10)]

    index.write_for_document(document_id=document_id, chunks=chunks)

    with psycopg.connect(TEST_DB_URL) as conn:
        count = conn.execute("SELECT COUNT(*) FROM chunks WHERE document_id = %s", (document_id,)).fetchone()[0]
    assert count == 10


def test_write_replace_existing_chunks(index):
    document_id = uuid4()

    first_batch_chunks = [_create_chunk(document_id=document_id, position=i) for i in range(3)]
    index.write_for_document(document_id=document_id, chunks=first_batch_chunks)

    second_batch_chunks = [_create_chunk(document_id=document_id, position=i) for i in range(5, 10)]
    index.write_for_document(document_id=document_id, chunks=second_batch_chunks)

    with psycopg.connect(TEST_DB_URL) as conn:
        rows = conn.execute("SELECT * FROM chunks WHERE document_id = %s", (document_id,)).fetchall()
    assert len(rows) == 5

    second_batch_ids = {chunk.chunk.id for chunk in second_batch_chunks}
    actual_ids = {row[0] for row in rows}
    assert actual_ids == second_batch_ids


def test_remove_for_document_deletes_all(index):    
    document_id = uuid4()
    chunks = [_create_chunk(document_id=document_id, position=i) for i in range(10)]
    index.write_for_document(document_id=document_id, chunks=chunks)

    index.remove_for_document(document_id=document_id)

    with psycopg.connect(TEST_DB_URL) as conn:
        count = conn.execute("SELECT COUNT(*) FROM chunks WHERE document_id = %s", (document_id,)).fetchone()[0]
    assert count == 0
            